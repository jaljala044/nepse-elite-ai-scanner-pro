"""Authenticated HTTP routes for private portfolio accounting."""
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .private_accounts import principal
from . import portfolio_service as service

router = APIRouter(prefix="/v1/portfolios", tags=["private-portfolios"])


class PortfolioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class PortfolioUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class PortfolioTransactionCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    side: str
    quantity: Decimal = Field(gt=0)
    price: Decimal = Field(gt=0)
    fees: Decimal = Field(default=Decimal("0"), ge=0)
    trade_date: str
    idempotency_key: str | None = Field(default=None, max_length=200)


def _owner(request: Request) -> str:
    return principal(request)


@router.get("")
def portfolios(request: Request):
    return {"portfolios": service.list_portfolios(_owner(request))}


@router.post("", status_code=201)
def create_portfolio(payload: PortfolioCreate, request: Request):
    try:
        return service.create_portfolio(_owner(request), payload.name)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/{portfolio_id}")
def get_portfolio(portfolio_id: str, request: Request):
    result = service.get_portfolio(_owner(request), portfolio_id)
    if result is None:
        raise HTTPException(404, "Portfolio not found")
    return result


@router.patch("/{portfolio_id}")
def update_portfolio(portfolio_id: str, payload: PortfolioUpdate, request: Request):
    try:
        result = service.update_portfolio(_owner(request), portfolio_id, payload.name)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if result is None:
        raise HTTPException(404, "Portfolio not found")
    return result


@router.delete("/{portfolio_id}", status_code=204)
def delete_portfolio(portfolio_id: str, request: Request):
    if not service.delete_portfolio(_owner(request), portfolio_id):
        raise HTTPException(404, "Portfolio not found")
    return None


@router.get("/{portfolio_id}/positions")
def positions(portfolio_id: str, request: Request):
    result = service.portfolio_positions(_owner(request), portfolio_id)
    if result is None:
        raise HTTPException(404, "Portfolio not found")
    return {
        "portfolio_id": portfolio_id,
        "positions": result,
        "valuation_note": "Market value and unrealized P&L remain UNKNOWN until an eligible, timestamped price source is connected.",
    }


@router.get("/{portfolio_id}/transactions")
def transactions(portfolio_id: str, request: Request):
    result = service.portfolio_transactions(_owner(request), portfolio_id)
    if result is None:
        raise HTTPException(404, "Portfolio not found")
    return {"portfolio_id": portfolio_id, "transactions": result}


@router.post("/{portfolio_id}/transactions", status_code=201)
def add_transaction(portfolio_id: str, payload: PortfolioTransactionCreate, request: Request):
    try:
        return service.add_transaction(
            _owner(request), portfolio_id, symbol=payload.symbol, side=payload.side,
            quantity=payload.quantity, price=payload.price, fees=payload.fees,
            trade_date=payload.trade_date,
            idempotency_key=payload.idempotency_key,
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc



class HoldingPreferenceUpdate(BaseModel):
    horizon: str
    risk_preference: str


@router.get("/{portfolio_id}/preferences")
def holding_preferences(portfolio_id: str, request: Request):
    result = service.list_holding_preferences(_owner(request), portfolio_id)
    if result is None:
        raise HTTPException(404, "Portfolio not found")
    return {"portfolio_id": portfolio_id, "preferences": result}


@router.put("/{portfolio_id}/preferences/{symbol}")
def update_holding_preference(portfolio_id: str, symbol: str,
                              payload: HoldingPreferenceUpdate, request: Request):
    try:
        return service.set_holding_preference(
            _owner(request), portfolio_id, symbol=symbol,
            horizon=payload.horizon, risk_preference=payload.risk_preference,
        )
    except LookupError as exc:
        raise HTTPException(404, "Portfolio not found") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
