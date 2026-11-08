import uuid
import logging
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from domain.models.bank import (
    FinancialTransaction,
    BankEscalation,
    FraudResponseStage,
    FinancialFundPosition
)
from domain.services.fraud_lifecycle_engine import FraudLifecycleEngine

logger = logging.getLogger(__name__)


class FinancialInvariantViolationError(ValueError):
    """Raised when monetary reconciliation violates strict financial accounting invariants."""
    pass


class FinancialReconciliationService:
    """
    Mathematical Invariants & Financial Reconciliation Engine.
    Resolves the secured-funds overlap problem by tracking distinct unique fund positions.
    Guarantees strict double-entry invariants across the financial fraud recovery lifecycle:
    0 <= amount_recovered <= amount_secured_unique <= identified_amount <= reported_loss
    """

    @classmethod
    def validate_invariants(
        cls,
        reported_loss: Decimal,
        identified_amount: Decimal,
        amount_under_lien: Decimal,
        amount_frozen: Decimal,
        amount_recovered: Decimal,
        amount_secured_unique: Optional[Decimal] = None,
        allow_identified_override: bool = False
    ) -> None:
        """
        Validates accounting invariants; raises FinancialInvariantViolationError if any are violated.
        If amount_secured_unique is provided, uses position-aware overlap accounting;
        otherwise falls back to (lien + frozen) for legacy compatibility.
        """
        # 1. Non-negativity check
        balances = {
            "reported_loss": reported_loss,
            "identified_amount": identified_amount,
            "amount_under_lien": amount_under_lien,
            "amount_frozen": amount_frozen,
            "amount_recovered": amount_recovered
        }
        if amount_secured_unique is not None:
            balances["amount_secured_unique"] = amount_secured_unique

        for name, val in balances.items():
            if val < Decimal("0.00"):
                raise FinancialInvariantViolationError(f"Invariant violation: {name} cannot be negative ({val}).")

        # 2. Identified transfer vs Reported loss
        if not allow_identified_override and identified_amount > reported_loss and reported_loss > Decimal("0.00"):
            raise FinancialInvariantViolationError(
                f"Invariant violation: Identified transfer (₹{identified_amount:,.2f}) cannot exceed "
                f"reported loss (₹{reported_loss:,.2f}) without amended evidence."
            )

        # 3. Secured funds cannot exceed identified transaction amount
        # Resolves overlap problem: amount_secured_unique prevents double-counting when liens become freezes
        total_secured = amount_secured_unique if amount_secured_unique is not None else (amount_under_lien + amount_frozen)
        if total_secured > identified_amount and identified_amount > Decimal("0.00"):
            raise FinancialInvariantViolationError(
                f"Invariant violation: Cumulative secured funds (₹{total_secured:,.2f}) "
                f"cannot exceed identified transfer amount (₹{identified_amount:,.2f})."
            )

        # 4. Recovered funds cannot exceed funds secured under lien or statutory freeze
        if amount_recovered > total_secured:
            raise FinancialInvariantViolationError(
                f"Invariant violation: Amount recovered (₹{amount_recovered:,.2f}) cannot exceed "
                f"funds secured under protective lien or freeze (₹{total_secured:,.2f})."
            )

    @classmethod
    async def record_or_update_fund_position(
        cls,
        db: AsyncSession,
        transaction_id: uuid.UUID,
        account_reference_masked: str,
        original_amount: Decimal,
        bank_id: Optional[uuid.UUID] = None,
        lien_delta: Decimal = Decimal("0.00"),
        frozen_delta: Decimal = Decimal("0.00"),
        recovered_delta: Decimal = Decimal("0.00"),
        source_reference: Optional[str] = None
    ) -> FinancialFundPosition:
        """
        Creates or updates a unique fund position for a beneficiary account or transfer leg.
        Resolves the lien-to-freeze overlap: position.secured_unique = max(lien, frozen).
        """
        # Look for existing position for this transaction and account
        stmt = (
            select(FinancialFundPosition)
            .where(
                FinancialFundPosition.transaction_id == transaction_id,
                FinancialFundPosition.account_reference_masked == account_reference_masked
            )
        )
        res = await db.execute(stmt)
        position = res.scalar_one_or_none()

        if not position:
            position = FinancialFundPosition(
                transaction_id=transaction_id,
                account_reference_masked=account_reference_masked,
                bank_id=bank_id,
                original_amount=original_amount,
                lien_amount=Decimal("0.00"),
                frozen_amount=Decimal("0.00"),
                recovered_amount=Decimal("0.00"),
                status="ACTIVE",
                source_reference=source_reference,
                version=1
            )
            db.add(position)
            await db.flush()

        new_lien = Decimal(str(position.lien_amount or 0.0)) + lien_delta
        new_frozen = Decimal(str(position.frozen_amount or 0.0)) + frozen_delta
        new_recovered = Decimal(str(position.recovered_amount or 0.0)) + recovered_delta

        # Check non-negativity
        if new_lien < Decimal("0.00") or new_frozen < Decimal("0.00") or new_recovered < Decimal("0.00"):
            raise FinancialInvariantViolationError("Fund position amounts cannot be negative.")

        # Invariant for this specific position: unique secured = max(lien, frozen)
        position_unique_secured = max(new_lien, new_frozen)
        orig = Decimal(str(position.original_amount))
        if position_unique_secured > orig and orig > Decimal("0.00"):
            raise FinancialInvariantViolationError(
                f"Fund position secured unique ₹{position_unique_secured:,.2f} exceeds original position amount ₹{orig:,.2f}."
            )
        if new_recovered > position_unique_secured:
            raise FinancialInvariantViolationError(
                f"Fund position recovered ₹{new_recovered:,.2f} exceeds secured amount ₹{position_unique_secured:,.2f}."
            )

        position.lien_amount = new_lien
        position.frozen_amount = new_frozen
        position.recovered_amount = new_recovered
        position.source_reference = source_reference or position.source_reference

        # Update position status
        if new_recovered >= orig and orig > Decimal("0.00"):
            position.status = "FULLY_RECOVERED"
        elif new_recovered > Decimal("0.00"):
            position.status = "PARTIALLY_RECOVERED"
        elif new_frozen > Decimal("0.00"):
            position.status = "FROZEN"
        elif new_lien > Decimal("0.00"):
            position.status = "LIEN_MARKED"
        else:
            position.status = "ACTIVE"

        position.version += 1
        await db.flush()
        return position

    @classmethod
    async def get_fund_positions_summary(
        cls,
        db: AsyncSession,
        transaction_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Calculates aggregate fund positions, computing amount_secured_unique to resolve overlaps.
        """
        stmt = (
            select(FinancialFundPosition)
            .where(FinancialFundPosition.transaction_id == transaction_id)
        )
        res = await db.execute(stmt)
        positions = res.scalars().all()

        total_original = Decimal("0.00")
        total_lien = Decimal("0.00")
        total_frozen = Decimal("0.00")
        total_recovered = Decimal("0.00")
        total_secured_unique = Decimal("0.00")

        positions_list = []
        for p in positions:
            p_orig = Decimal(str(p.original_amount))
            p_lien = Decimal(str(p.lien_amount or 0.0))
            p_frozen = Decimal(str(p.frozen_amount or 0.0))
            p_rec = Decimal(str(p.recovered_amount or 0.0))
            p_sec_unique = max(p_lien, p_frozen)

            total_original += p_orig
            total_lien += p_lien
            total_frozen += p_frozen
            total_recovered += p_rec
            total_secured_unique += p_sec_unique

            positions_list.append({
                "id": str(p.id),
                "account_reference_masked": p.account_reference_masked,
                "original_amount": str(p_orig),
                "lien_amount": str(p_lien),
                "frozen_amount": str(p_frozen),
                "recovered_amount": str(p_rec),
                "secured_unique": str(p_sec_unique),
                "status": p.status
            })

        return {
            "total_positions_count": len(positions),
            "total_original": total_original,
            "total_lien": total_lien,
            "total_frozen": total_frozen,
            "total_recovered": total_recovered,
            "total_secured_unique": total_secured_unique,
            "positions": positions_list
        }

    @classmethod
    async def reconcile_transaction(
        cls,
        db: AsyncSession,
        transaction_id: uuid.UUID,
        new_lien_delta: Decimal = Decimal("0.00"),
        new_frozen_delta: Decimal = Decimal("0.00"),
        new_recovered_delta: Decimal = Decimal("0.00"),
        correlation_id: Optional[str] = None,
        actor: str = "SERVICE:FinancialReconciliationService",
        reason: str = "Bank action report processed",
        fund_position_account: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Applies incremental monetary deltas, validates mathematical invariants with overlap resolution,
        updates the FinancialTransaction record and fund position ledger,
        and records a reconciliation lifecycle event.
        """
        res = await db.execute(
            select(FinancialTransaction).where(FinancialTransaction.id == transaction_id)
        )
        fin_txn = res.scalar_one_or_none()
        if not fin_txn:
            raise ValueError(f"Financial transaction {transaction_id} not found.")

        current_rep = Decimal(str(fin_txn.reported_loss_amount or fin_txn.amount))
        current_id = Decimal(str(fin_txn.amount))
        current_lien = Decimal(str(fin_txn.amount_under_lien or 0.0))
        current_frozen = Decimal(str(fin_txn.amount_frozen or 0.0))
        current_rec = Decimal(str(fin_txn.amount_recovered or 0.0))

        # If a specific account fund position is referenced, record it in the ledger
        if fund_position_account or fin_txn.beneficiary_account_masked:
            acct_ref = fund_position_account or fin_txn.beneficiary_account_masked
            await cls.record_or_update_fund_position(
                db=db,
                transaction_id=transaction_id,
                account_reference_masked=acct_ref,
                original_amount=current_id,
                bank_id=fin_txn.beneficiary_bank_id,
                lien_delta=new_lien_delta,
                frozen_delta=new_frozen_delta,
                recovered_delta=new_recovered_delta,
                source_reference=reason
            )

        updated_lien = current_lien + new_lien_delta
        updated_frozen = current_frozen + new_frozen_delta
        updated_rec = current_rec + new_recovered_delta

        # Check if fund positions exist to calculate unique secured funds
        pos_summary = await cls.get_fund_positions_summary(db, transaction_id)
        if pos_summary["total_positions_count"] > 0:
            amount_secured_unique = pos_summary["total_secured_unique"]
        else:
            # Overlap fallback if lien is converted to freeze on the same single transaction
            amount_secured_unique = max(updated_lien, updated_frozen)

        # Strictly enforce invariants before writing to database
        cls.validate_invariants(
            reported_loss=current_rep,
            identified_amount=current_id,
            amount_under_lien=updated_lien,
            amount_frozen=updated_frozen,
            amount_recovered=updated_rec,
            amount_secured_unique=amount_secured_unique
        )

        # Commit validated balances
        fin_txn.amount_under_lien = updated_lien
        fin_txn.amount_frozen = updated_frozen
        fin_txn.amount_recovered = updated_rec
        await db.flush()

        amount_unresolved = max(Decimal("0.00"), current_rep - amount_secured_unique)

        snapshot = {
            "reported_loss_inr": str(current_rep),
            "identified_transfer_inr": str(current_id),
            "amount_under_lien_inr": str(updated_lien),
            "amount_frozen_inr": str(updated_frozen),
            "amount_secured_unique_inr": str(amount_secured_unique),
            "amount_recovered_inr": str(updated_rec),
            "amount_unresolved_inr": str(amount_unresolved)
        }

        # Record stage 8: FINANCIAL_STATUS_RECONCILED
        corr_id = correlation_id or f"CID-TXN-{transaction_id.hex[:8].upper()}"
        await FraudLifecycleEngine.record_transition(
            db=db,
            correlation_id=corr_id,
            case_id=fin_txn.case_id,
            stage=FraudResponseStage.FINANCIAL_STATUS_RECONCILED,
            actor_or_service=actor,
            transition_reason=reason,
            transaction_id=fin_txn.id,
            financial_snapshot=snapshot
        )

        return {
            "success": True,
            "transaction_id": str(fin_txn.id),
            "financial_snapshot": snapshot,
            "fund_positions_count": pos_summary["total_positions_count"],
            "correlation_id": corr_id
        }
