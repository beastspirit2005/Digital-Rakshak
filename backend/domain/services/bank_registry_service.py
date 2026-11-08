import uuid
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from domain.models.bank import BankRegistry, BankIntegrationType

logger = logging.getLogger(__name__)

# Canonical seed directory of major Indian Financial Institutions
INITIAL_VERIFIED_BANKS: List[Dict[str, Any]] = [
    {
        "bank_code": "SBIN",
        "bank_name": "State Bank of India",
        "rbi_code": "002",
        "ifsc_prefix": "SBIN",
        "supported_rails": ["UPI", "IMPS", "NEFT", "RTGS"],
        "nodal_email": "cybercrime.nodal@sbi.co.in",
        "integration_type": BankIntegrationType.SANDBOX_API.value,
        "api_endpoint": "https://api-sandbox.digitalrakshak.gov.in/banks/sbin/v1/fraud-alerts",
    },
    {
        "bank_code": "HDFC",
        "bank_name": "HDFC Bank Ltd.",
        "rbi_code": "240",
        "ifsc_prefix": "HDFC",
        "supported_rails": ["UPI", "IMPS", "NEFT", "RTGS"],
        "nodal_email": "fraud.reporting@hdfcbank.com",
        "integration_type": BankIntegrationType.SANDBOX_API.value,
        "api_endpoint": "https://api-sandbox.digitalrakshak.gov.in/banks/hdfc/v1/fraud-alerts",
    },
    {
        "bank_code": "ICIC",
        "bank_name": "ICICI Bank Ltd.",
        "rbi_code": "229",
        "ifsc_prefix": "ICIC",
        "supported_rails": ["UPI", "IMPS", "NEFT", "RTGS"],
        "nodal_email": "anti.fraud@icicibank.com",
        "integration_type": BankIntegrationType.SANDBOX_API.value,
        "api_endpoint": "https://api-sandbox.digitalrakshak.gov.in/banks/icic/v1/fraud-alerts",
    },
    {
        "bank_code": "AXIS",
        "bank_name": "Axis Bank Ltd.",
        "rbi_code": "211",
        "ifsc_prefix": "UTIB",
        "supported_rails": ["UPI", "IMPS", "NEFT", "RTGS"],
        "nodal_email": "cybercell.escalation@axisbank.com",
        "integration_type": BankIntegrationType.SANDBOX_API.value,
        "api_endpoint": "https://api-sandbox.digitalrakshak.gov.in/banks/axis/v1/fraud-alerts",
    },
    {
        "bank_code": "PUNB",
        "bank_name": "Punjab National Bank",
        "rbi_code": "024",
        "ifsc_prefix": "PUNB",
        "supported_rails": ["UPI", "IMPS", "NEFT", "RTGS"],
        "nodal_email": "nodal.cybercell@pnb.co.in",
        "integration_type": BankIntegrationType.SANDBOX_API.value,
        "api_endpoint": "https://api-sandbox.digitalrakshak.gov.in/banks/punb/v1/fraud-alerts",
    },
    {
        "bank_code": "BARB",
        "bank_name": "Bank of Baroda",
        "rbi_code": "012",
        "ifsc_prefix": "BARB",
        "supported_rails": ["UPI", "IMPS", "NEFT", "RTGS"],
        "nodal_email": "ciso.cybercell@bankofbaroda.com",
        "integration_type": BankIntegrationType.SANDBOX_API.value,
        "api_endpoint": "https://api-sandbox.digitalrakshak.gov.in/banks/barb/v1/fraud-alerts",
    },
    {
        "bank_code": "CNRB",
        "bank_name": "Canara Bank",
        "rbi_code": "015",
        "ifsc_prefix": "CNRB",
        "supported_rails": ["UPI", "IMPS", "NEFT", "RTGS"],
        "nodal_email": "cyberdesk@canarabank.com",
        "integration_type": BankIntegrationType.SANDBOX_API.value,
        "api_endpoint": "https://api-sandbox.digitalrakshak.gov.in/banks/cnrb/v1/fraud-alerts",
    },
    {
        "bank_code": "UBIN",
        "bank_name": "Union Bank of India",
        "rbi_code": "026",
        "ifsc_prefix": "UBIN",
        "supported_rails": ["UPI", "IMPS", "NEFT", "RTGS"],
        "nodal_email": "cybercrime.desk@unionbankofindia.bank",
        "integration_type": BankIntegrationType.SANDBOX_API.value,
        "api_endpoint": "https://api-sandbox.digitalrakshak.gov.in/banks/ubin/v1/fraud-alerts",
    },
    {
        "bank_code": "KKBK",
        "bank_name": "Kotak Mahindra Bank Ltd.",
        "rbi_code": "236",
        "ifsc_prefix": "KKBK",
        "supported_rails": ["UPI", "IMPS", "NEFT", "RTGS"],
        "nodal_email": "cyberfraudescalation@kotak.com",
        "integration_type": BankIntegrationType.SANDBOX_API.value,
        "api_endpoint": "https://api-sandbox.digitalrakshak.gov.in/banks/kkbk/v1/fraud-alerts",
    },
    {
        "bank_code": "IDFB",
        "bank_name": "IDFC FIRST Bank Ltd.",
        "rbi_code": "242",
        "ifsc_prefix": "IDFB",
        "supported_rails": ["UPI", "IMPS", "NEFT", "RTGS"],
        "nodal_email": "fraudcontrol@idfcfirstbank.com",
        "integration_type": BankIntegrationType.SANDBOX_API.value,
        "api_endpoint": "https://api-sandbox.digitalrakshak.gov.in/banks/idfb/v1/fraud-alerts",
    },
    {
        "bank_code": "YESB",
        "bank_name": "YES Bank Ltd.",
        "rbi_code": "234",
        "ifsc_prefix": "YESB",
        "supported_rails": ["UPI", "IMPS", "NEFT", "RTGS"],
        "nodal_email": "nodal.cyber@yesbank.in",
        "integration_type": BankIntegrationType.SANDBOX_API.value,
        "api_endpoint": "https://api-sandbox.digitalrakshak.gov.in/banks/yesb/v1/fraud-alerts",
    },
    {
        "bank_code": "INDB",
        "bank_name": "IndusInd Bank Ltd.",
        "rbi_code": "233",
        "ifsc_prefix": "INDB",
        "supported_rails": ["UPI", "IMPS", "NEFT", "RTGS"],
        "nodal_email": "cyberdesk@indusind.com",
        "integration_type": BankIntegrationType.SANDBOX_API.value,
        "api_endpoint": "https://api-sandbox.digitalrakshak.gov.in/banks/indb/v1/fraud-alerts",
    },
    {
        "bank_code": "PYTM",
        "bank_name": "Paytm Payments Bank",
        "rbi_code": "501",
        "ifsc_prefix": "PYTM",
        "supported_rails": ["UPI", "IMPS", "WALLET"],
        "nodal_email": "cybercell.nodal@paytmbank.com",
        "integration_type": BankIntegrationType.SANDBOX_API.value,
        "api_endpoint": "https://api-sandbox.digitalrakshak.gov.in/banks/pytm/v1/fraud-alerts",
    },
    {
        "bank_code": "AIRP",
        "bank_name": "Airtel Payments Bank",
        "rbi_code": "502",
        "ifsc_prefix": "AIRP",
        "supported_rails": ["UPI", "IMPS", "WALLET"],
        "nodal_email": "cybercrime.escalations@airtelbank.com",
        "integration_type": BankIntegrationType.SANDBOX_API.value,
        "api_endpoint": "https://api-sandbox.digitalrakshak.gov.in/banks/airp/v1/fraud-alerts",
    },
    {
        "bank_code": "IPOS",
        "bank_name": "India Post Payments Bank",
        "rbi_code": "503",
        "ifsc_prefix": "IPOS",
        "supported_rails": ["UPI", "IMPS", "NEFT"],
        "nodal_email": "cyberdesk@ippbonline.in",
        "integration_type": BankIntegrationType.SANDBOX_API.value,
        "api_endpoint": "https://api-sandbox.digitalrakshak.gov.in/banks/ipos/v1/fraud-alerts",
    },
    {
        "bank_code": "CBIN",
        "bank_name": "Central Bank of India",
        "rbi_code": "016",
        "ifsc_prefix": "CBIN",
        "supported_rails": ["UPI", "IMPS", "NEFT", "RTGS"],
        "nodal_email": "cybercrime@centralbank.co.in",
        "integration_type": BankIntegrationType.SANDBOX_API.value,
        "api_endpoint": "https://api-sandbox.digitalrakshak.gov.in/banks/cbin/v1/fraud-alerts",
    },
    {
        "bank_code": "IDIB",
        "bank_name": "Indian Bank",
        "rbi_code": "019",
        "ifsc_prefix": "IDIB",
        "supported_rails": ["UPI", "IMPS", "NEFT", "RTGS"],
        "nodal_email": "cybercell@indianbank.co.in",
        "integration_type": BankIntegrationType.SANDBOX_API.value,
        "api_endpoint": "https://api-sandbox.digitalrakshak.gov.in/banks/idib/v1/fraud-alerts",
    },
    {
        "bank_code": "BKID",
        "bank_name": "Bank of India",
        "rbi_code": "013",
        "ifsc_prefix": "BKID",
        "supported_rails": ["UPI", "IMPS", "NEFT", "RTGS"],
        "nodal_email": "cyberdesk@bankofindia.co.in",
        "integration_type": BankIntegrationType.SANDBOX_API.value,
        "api_endpoint": "https://api-sandbox.digitalrakshak.gov.in/banks/bkid/v1/fraud-alerts",
    },
    {
        "bank_code": "FDRL",
        "bank_name": "Federal Bank Ltd.",
        "rbi_code": "213",
        "ifsc_prefix": "FDRL",
        "supported_rails": ["UPI", "IMPS", "NEFT", "RTGS"],
        "nodal_email": "cybercell@federalbank.co.in",
        "integration_type": BankIntegrationType.SANDBOX_API.value,
        "api_endpoint": "https://api-sandbox.digitalrakshak.gov.in/banks/fdrl/v1/fraud-alerts",
    },
    {
        "bank_code": "IBKL",
        "bank_name": "IDBI Bank Ltd.",
        "rbi_code": "018",
        "ifsc_prefix": "IBKL",
        "supported_rails": ["UPI", "IMPS", "NEFT", "RTGS"],
        "nodal_email": "cybercrime.support@idbi.co.in",
        "integration_type": BankIntegrationType.SANDBOX_API.value,
        "api_endpoint": "https://api-sandbox.digitalrakshak.gov.in/banks/ibkl/v1/fraud-alerts",
    }
]

# Standard VPA Handle to Bank Code / PSP mappings in Indian UPI ecosystem
VPA_HANDLE_TO_BANK_CODE: Dict[str, str] = {
    "okaxis": "AXIS",
    "okhdfcbank": "HDFC",
    "okicici": "ICIC",
    "oksbi": "SBIN",
    "ybl": "YESB",
    "ibl": "ICIC",
    "axl": "AXIS",
    "paytm": "PYTM",
    "airtel": "AIRP",
    "sbi": "SBIN",
    "hdfcbank": "HDFC",
    "icici": "ICIC",
    "kotak": "KKBK",
    "barodampay": "BARB",
    "cnrb": "CNRB",
    "unionbank": "UBIN",
    "pnb": "PUNB",
    "indus": "INDB",
    "idfcbank": "IDFB",
    "federal": "FDRL",
    "centralbank": "CBIN",
    "indianbank": "IDIB",
    "allbank": "IDIB",
    "postbank": "IPOS",
}


class BankRegistryService:
    """
    Manages Verified Bank Directory and IFSC / VPA resolution.
    """

    @classmethod
    async def seed_verified_banks(cls, db: AsyncSession) -> int:
        """
        Seeds canonical Indian banks into the bank_registry table if not already present.
        Returns the number of banks newly inserted.
        """
        inserted_count = 0
        for bank_data in INITIAL_VERIFIED_BANKS:
            existing = await db.execute(
                select(BankRegistry).where(BankRegistry.bank_code == bank_data["bank_code"])
            )
            if not existing.scalar_one_or_none():
                new_bank = BankRegistry(
                    bank_code=bank_data["bank_code"],
                    bank_name=bank_data["bank_name"],
                    rbi_code=bank_data.get("rbi_code"),
                    ifsc_prefix=bank_data["ifsc_prefix"],
                    supported_rails=bank_data["supported_rails"],
                    escalation_channels=bank_data.get("escalation_channels", {"api": True, "nodal_email": True}),
                    integration_type=bank_data.get("integration_type", BankIntegrationType.SANDBOX_API.value),
                    api_endpoint=bank_data.get("api_endpoint"),
                    nodal_email=bank_data.get("nodal_email"),
                    is_active=True
                )
                db.add(new_bank)
                inserted_count += 1
        
        if inserted_count > 0:
            await db.commit()
            logger.info(f"Seeded {inserted_count} banks into bank_registry.")
        return inserted_count

    @classmethod
    async def get_bank_by_code(cls, db: AsyncSession, bank_code: str) -> Optional[BankRegistry]:
        """Fetch bank by unique bank code (case-insensitive)."""
        if not bank_code:
            return None
        res = await db.execute(
            select(BankRegistry).where(BankRegistry.bank_code == bank_code.upper().strip())
        )
        return res.scalar_one_or_none()

    @classmethod
    async def get_bank_by_ifsc_prefix(cls, db: AsyncSession, ifsc_prefix: str) -> Optional[BankRegistry]:
        """Fetch bank by 4-letter IFSC prefix."""
        if not ifsc_prefix:
            return None
        prefix = ifsc_prefix.upper().strip()[:4]
        res = await db.execute(
            select(BankRegistry).where(BankRegistry.ifsc_prefix == prefix)
        )
        return res.scalar_one_or_none()

    @classmethod
    async def resolve_bank_from_ifsc(cls, db: AsyncSession, ifsc_code: str) -> Optional[BankRegistry]:
        """
        Resolves bank from an 11-character Indian Financial System Code.
        e.g. SBIN0001234 -> SBIN (State Bank of India)
             UTIB0000001 -> UTIB (Axis Bank)
        """
        if not ifsc_code or len(ifsc_code.strip()) < 4:
            return None
        clean_ifsc = ifsc_code.strip().upper()
        prefix = clean_ifsc[:4]
        return await cls.get_bank_by_ifsc_prefix(db, prefix)

    @classmethod
    async def resolve_bank_from_vpa(cls, db: AsyncSession, vpa: str) -> Optional[BankRegistry]:
        """
        Resolves issuing PSP / bank from a Virtual Payment Address handle.
        e.g. user@okhdfcbank -> HDFC Bank
             merchant@ybl -> YES Bank
        """
        if not vpa or "@" not in vpa:
            return None
        handle = vpa.strip().lower().split("@")[-1]
        bank_code = VPA_HANDLE_TO_BANK_CODE.get(handle)
        if bank_code:
            return await cls.get_bank_by_code(db, bank_code)
        return None

    @classmethod
    async def list_banks(cls, db: AsyncSession, only_active: bool = True) -> List[BankRegistry]:
        """List all verified institutions in directory."""
        query = select(BankRegistry)
        if only_active:
            query = query.where(BankRegistry.is_active == True)
        query = query.order_by(BankRegistry.bank_name.asc())
        res = await db.execute(query)
        return list(res.scalars().all())
