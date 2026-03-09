'''All database CRUD operations are defined here.'''

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from models import User, Account, Statement, Transaction

# -------------------------
# USER CRUD
# -------------------------

async def create_financial_account(session: AsyncSession, user_id: int, name: str) -> Account:
    account = Account(name=name, user_id=user_id)
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account

async def get_financial_accounts(session: AsyncSession, user_id: int) -> list[Account]:
    result = await session.execute(
        select(Account).where(Account.user_id == user_id)
    )
    return result.scalars().all()


async def get_financial_account(session: AsyncSession, account_id: int, user_id: int) -> Account | None:
    result = await session.execute(
        select(Account).where(Account.id == account_id, Account.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def delete_financial_account(session: AsyncSession, account_id: int, user_id: int) -> bool:
    account = await get_financial_account(session, account_id, user_id)
    if not account:
        return False
    await session.delete(account)
    await session.commit()
    return True


# -------------------------
# STATEMENTS
# -------------------------

async def create_statement(
    session: AsyncSession,
    account_id: int,
    account_number: str | None,
    start_date: str,
    end_date: str,
    opening_balance: float | None,
    closing_balance: float | None,
) -> Statement:
    statement = Statement(
        account_id=account_id,
        account_number=account_number,
        start_date=start_date,
        end_date=end_date,
        opening_balance=opening_balance,
        closing_balance=closing_balance,
    )
    session.add(statement)
    await session.commit()
    await session.refresh(statement)
    return statement


async def get_statements(session: AsyncSession, account_id: int) -> list[Statement]:
    result = await session.execute(
        select(Statement).where(Statement.account_id == account_id)
    )
    return result.scalars().all()


async def get_statement(session: AsyncSession, statement_id: int) -> Statement | None:
    result = await session.execute(
        select(Statement).where(Statement.id == statement_id)
    )
    return result.scalar_one_or_none()


async def delete_statement(session: AsyncSession, statement_id: int) -> bool:
    statement = await get_statement(session, statement_id)
    if not statement:
        return False
    await session.delete(statement)
    await session.commit()
    return True


# -------------------------
# TRANSACTIONS
# -------------------------

async def create_transactions(
    session: AsyncSession,
    statement_id: int,
    transactions: list[dict],
) -> list[Transaction]:
    db_transactions = [
        Transaction(
            statement_id=statement_id,
            date=txn["date"],
            description=txn.get("description"),
            amount=txn.get("amount"),
            balance=txn.get("balance"),
            type=txn["type"],
            category=txn.get("category"),
        )
        for txn in transactions
    ]
    session.add_all(db_transactions)
    await session.commit()
    return db_transactions


async def get_transactions(session: AsyncSession, statement_id: int) -> list[Transaction]:
    result = await session.execute(
        select(Transaction).where(Transaction.statement_id == statement_id)
    )
    return result.scalars().all()


async def get_transactions_by_account(session: AsyncSession, account_id: int) -> list[Transaction]:
    """Get all transactions across all statements for an account — used for trends."""
    result = await session.execute(
        select(Transaction)
        .join(Statement)
        .where(Statement.account_id == account_id)
        .order_by(Transaction.date)
    )
    return result.scalars().all()
