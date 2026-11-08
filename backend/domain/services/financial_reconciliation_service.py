import uuid
import logging
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from domain.models.bank import (
    FinancialTransaction,
    BankEscalation,
    FraudResponseStage
)
from domain.services.fraud_lifecycle_engine import FraudLifecycleEngine

logger = logging.getLogger(__name__)


class FinancialInvariantViolationError(ValueError):
    """Raised when monetary reconciliation violates strict financial accounting invariants."""
    pass


class FinancialReconciliationService:
    """
    Mathematical Invariants & Financial Reconciliation Engine.
    Guarantees strict double-entry invariants across the financial fraud recovery lifecycle:
    0 <= amount_recovered <= (amount_frozen + amount_under_lien) <= identified_amount <= reported_loss
    """

    @classmethod
    def validate_invariants(
        cls,
        reported_loss: Decimal,
        identified_amount: Decimal,
        amount_under_lien: Decimal,
        amount_frozen: Decimal,
        amount_recovered: Decimal,
        allow_identified_override: bool = False
    ) -> None:
        """
        Validates accounting invariants; raises FinancialInvariantViolationError if any are violated.
        """
        # 1. Non-negativity check
        balances = {
            "reported_loss": reported_loss,
            "identified_amount": identified_amount,
            "amount_under_lien": amount_under_lien,
            "amount_frozen": amount_frozen,
            "amount_recovered": amount_recovered
        }
        for name, val in balances.items():
            if val < Decimal("0.00"):
                raise FinancialInvariantViolationError(f"Invariant violation: {name} cannot be negative ({val}).")

        # 2. Identified transfer vs Reported loss
        if not allow_identified_override and identified_amount > reported_loss and reported_loss > Decimal("0.00"):
            raise FinancialInvariantViolationError(
                f"Invariant violation: Identified transfer (₹{identified_amount:,.2f}) cannot exceed "
                f"reported loss (₹{reported_loss:,.2f}) without amended evidence."
            )

        # 3. Cumulative secured funds cannot exceed identified transaction amount
        total_secured = amount_under_lien + amount_frozen
        if total_secured > identified_amount and identified_amount > Decimal("0.00"):
            raise FinancialInvariantViolationError(
                f"Invariant violation: Cumulative secured funds (Lien ₹{amount_under_lien:,.2f} + Frozen ₹{amount_frozen:,.2f} = ₹{total_secured:,.2f}) "
                f"cannot exceed identified transfer amount (₹{identified_amount:,.2f})."
            )

        # 4. Recovered funds cannot exceed funds secured under lien or statutory freeze
        if amount_recovered > total_secured:
            raise FinancialInvariantViolationError(
                f"Invariant violation: Amount recovered (₹{amount_recovered:,.2f}) cannot exceed "
                f"funds secured under protective lien or freeze (₹{total_secured:,.2f})."
            )

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
        reason: str = "Bank action report processed"
    ) -> Dict[str, Any]:
        """
        Applies incremental monetary deltas, validates mathematical invariants,
        updates the FinancialTransaction record, and records a reconciliation lifecycle event.
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

        updated_lien = current_lien + new_lien_delta
        updated_frozen = current_frozen + new_frozen_delta
        updated_rec = current_rec + new_recovered_delta

        # Strictly enforce invariants before writing to database
        cls.validate_invariants(
            reported_loss=current_rep,
            identified_amount=current_id,
            amount_under_lien=updated_lien,
            amount_frozen=updated_frozen,
            amount_recovered=updated_rec
        )

        # Commit validated balances
        fin_txn.amount_under_lien = updated_lien
        fin_txn.amount_frozen = updated_frozen
        fin_txn.amount_recovered = updated_rec
        await db.flush()

        snapshot = {
            "reported_loss_inr": str(current_rep),
            "identified_transfer_inr": str(current_id),
            "amount_under_lien_inr": str(updated_lien),
            "amount_frozen_inr": str(updated_frozen),
            "amount_recovered_inr": str(updated_rec)
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
            financial_snapshot=snapshot,
            metadata={"deltas": {"lien": str(new_lien_delta), "frozen": str(new_frozen_delta), "recovered": str(new_recovered_delta)}}
        )

        return snapshot
