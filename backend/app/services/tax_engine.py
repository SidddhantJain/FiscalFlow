"""
Indian Statutory Tax Engine (Finance Act 2024 / FY 2024-25 & FY 2025-26)
Compliant with Income Tax Act, 1961:
- Section 115BAC (New Tax Regime - Default) with ₹75,000 Standard Deduction
- Old Tax Regime with Chapter VI-A statutory caps (80C ₹1.5L, 80D ₹25k, 80CCD(1B) ₹50k)
- Section 87A Rebate (up to ₹7,00,000 in New Regime, ₹5,00,000 in Old Regime)
- Marginal Relief provisions u/s 87A
- 4% Health & Education Cess
- Section 111A: Short-Term Capital Gains (STCG @ 20%)
- Section 112A: Long-Term Capital Gains (LTCG @ 12.5% with ₹1,25,000 statutory exemption)
- 365-day holding period threshold for listed equity
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import Dict, Any, List, Optional


def round_curr(val: float) -> float:
    return float(Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


# ==============================================================================
# 1. NEW TAX REGIME (Section 115BAC - Finance Act 2024)
# ==============================================================================

def compute_new_regime_tax(gross_income: float, is_salaried: bool = True) -> Dict[str, Any]:
    """
    Computes tax liability under Section 115BAC (New Tax Regime) as per Finance Act 2024.
    - Standard deduction for salaried: ₹75,000
    - Slabs:
        0 - 3,00,000        : Nil
        3,00,001 - 7,00,000 : 5%
        7,00,001 - 10,00,000: 10%
        10,00,001 - 12,00,000: 15%
        12,00,001 - 15,00,000: 20%
        Above 15,00,000     : 30%
    - Section 87A Rebate:
        If taxable income <= ₹7,00,000, 100% tax rebate (up to ₹25,000).
        Marginal relief: If taxable income slightly exceeds ₹7,00,000, tax cannot exceed (taxable income - ₹7,00,000).
    - Health & Education Cess: 4%
    """
    gross = max(0.0, float(gross_income))
    standard_deduction = 75000.0 if is_salaried else 0.0
    taxable_income = max(0.0, gross - standard_deduction)

    # Calculate slab breakdown
    slab_breakdown = []
    slab_tax = 0.0

    # Slab 1: 0 to 3,00,000 @ 0%
    taxable_s1 = min(taxable_income, 300000.0)
    slab_breakdown.append({"slab": "₹0 - ₹3,00,000", "rate": "0%", "taxable_amount": taxable_s1, "tax": 0.0})

    # Slab 2: 3,00,001 to 7,00,000 @ 5%
    if taxable_income > 300000.0:
        taxable_s2 = min(taxable_income - 300000.0, 400000.0)
        t2 = taxable_s2 * 0.05
        slab_tax += t2
        slab_breakdown.append({"slab": "₹3,00,001 - ₹7,00,000", "rate": "5%", "taxable_amount": taxable_s2, "tax": round_curr(t2)})

    # Slab 3: 7,00,001 to 10,00,000 @ 10%
    if taxable_income > 700000.0:
        taxable_s3 = min(taxable_income - 700000.0, 300000.0)
        t3 = taxable_s3 * 0.10
        slab_tax += t3
        slab_breakdown.append({"slab": "₹7,00,001 - ₹10,00,000", "rate": "10%", "taxable_amount": taxable_s3, "tax": round_curr(t3)})

    # Slab 4: 10,00,001 to 12,00,000 @ 15%
    if taxable_income > 1000000.0:
        taxable_s4 = min(taxable_income - 1000000.0, 200000.0)
        t4 = taxable_s4 * 0.15
        slab_tax += t4
        slab_breakdown.append({"slab": "₹10,00,001 - ₹12,00,000", "rate": "15%", "taxable_amount": taxable_s4, "tax": round_curr(t4)})

    # Slab 5: 12,00,001 to 15,00,000 @ 20%
    if taxable_income > 1200000.0:
        taxable_s5 = min(taxable_income - 1200000.0, 300000.0)
        t5 = taxable_s5 * 0.20
        slab_tax += t5
        slab_breakdown.append({"slab": "₹12,00,001 - ₹15,00,000", "rate": "20%", "taxable_amount": taxable_s5, "tax": round_curr(t5)})

    # Slab 6: Above 15,00,000 @ 30%
    if taxable_income > 1500000.0:
        taxable_s6 = taxable_income - 1500000.0
        t6 = taxable_s6 * 0.30
        slab_tax += t6
        slab_breakdown.append({"slab": "Above ₹15,00,000", "rate": "30%", "taxable_amount": taxable_s6, "tax": round_curr(t6)})

    # Section 87A Rebate & Marginal Relief
    rebate_87a = 0.0
    marginal_relief = 0.0
    tax_after_rebate = slab_tax

    if taxable_income <= 700000.0:
        # Full rebate up to ₹25,000
        rebate_87a = min(slab_tax, 25000.0)
        tax_after_rebate = 0.0
    else:
        # Check Section 87A Marginal Relief:
        # Income exceeding ₹7,00,000
        excess_income = taxable_income - 700000.0
        if slab_tax > excess_income:
            marginal_relief = slab_tax - excess_income
            tax_after_rebate = excess_income

    cess_4_pct = tax_after_rebate * 0.04
    total_tax = tax_after_rebate + cess_4_pct

    effective_rate_pct = (total_tax / gross * 100.0) if gross > 0 else 0.0

    return {
        "regime": "NEW_TAX_REGIME_115BAC",
        "legal_basis": "Finance Act 2024 (Section 115BAC)",
        "gross_income": round_curr(gross),
        "standard_deduction": round_curr(standard_deduction),
        "taxable_income": round_curr(taxable_income),
        "tax_before_rebate": round_curr(slab_tax),
        "rebate_87a": round_curr(rebate_87a),
        "marginal_relief_87a": round_curr(marginal_relief),
        "tax_after_rebate": round_curr(tax_after_rebate),
        "cess_4_pct": round_curr(cess_4_pct),
        "total_tax": round_curr(total_tax),
        "effective_rate_pct": round(effective_rate_pct, 2),
        "slab_breakdown": slab_breakdown
    }


# ==============================================================================
# 2. OLD TAX REGIME (With Statutory Caps on Deductions)
# ==============================================================================

def compute_old_regime_tax(
    gross_income: float,
    deductions_80c: float = 0.0,
    deductions_80d: float = 0.0,
    deductions_nps_80ccd1b: float = 0.0,
    deductions_home_loan_24b: float = 0.0,
    is_salaried: bool = True
) -> Dict[str, Any]:
    """
    Computes tax liability under Old Tax Regime with strictly enforced statutory caps:
    - Standard deduction: ₹50,000
    - Section 80C: Capped at ₹1,50,000
    - Section 80D: Capped at ₹25,000 (standard health insurance)
    - Section 80CCD(1B): Additional NPS capped at ₹50,000
    - Section 24(b): Home loan interest capped at ₹2,00,000
    - Slabs:
        0 - 2,50,000        : Nil
        2,50,001 - 5,00,000 : 5%
        5,00,001 - 10,00,000: 20%
        Above 10,00,000     : 30%
    - Section 87A Rebate:
        If taxable income <= ₹5,00,000, 100% tax rebate (up to ₹12,500).
    - Health & Education Cess: 4%
    """
    gross = max(0.0, float(gross_income))
    standard_deduction = 50000.0 if is_salaried else 0.0

    # Strictly enforced statutory caps
    capped_80c = min(max(0.0, float(deductions_80c)), 150000.0)
    capped_80d = min(max(0.0, float(deductions_80d)), 25000.0)
    capped_80ccd1b = min(max(0.0, float(deductions_nps_80ccd1b)), 50000.0)
    capped_24b = min(max(0.0, float(deductions_home_loan_24b)), 200000.0)

    total_deductions = standard_deduction + capped_80c + capped_80d + capped_80ccd1b + capped_24b
    taxable_income = max(0.0, gross - total_deductions)

    slab_breakdown = []
    slab_tax = 0.0

    # Slab 1: 0 to 2,50,000 @ 0%
    taxable_s1 = min(taxable_income, 250000.0)
    slab_breakdown.append({"slab": "₹0 - ₹2,50,000", "rate": "0%", "taxable_amount": taxable_s1, "tax": 0.0})

    # Slab 2: 2,50,001 to 5,00,000 @ 5%
    if taxable_income > 250000.0:
        taxable_s2 = min(taxable_income - 250000.0, 250000.0)
        t2 = taxable_s2 * 0.05
        slab_tax += t2
        slab_breakdown.append({"slab": "₹2,50,001 - ₹5,00,000", "rate": "5%", "taxable_amount": taxable_s2, "tax": round_curr(t2)})

    # Slab 3: 5,00,001 to 10,00,000 @ 20%
    if taxable_income > 500000.0:
        taxable_s3 = min(taxable_income - 500000.0, 500000.0)
        t3 = taxable_s3 * 0.20
        slab_tax += t3
        slab_breakdown.append({"slab": "₹5,00,001 - ₹10,00,000", "rate": "20%", "taxable_amount": taxable_s3, "tax": round_curr(t3)})

    # Slab 4: Above 10,00,000 @ 30%
    if taxable_income > 1000000.0:
        taxable_s4 = taxable_income - 1000000.0
        t4 = taxable_s4 * 0.30
        slab_tax += t4
        slab_breakdown.append({"slab": "Above ₹10,00,000", "rate": "30%", "taxable_amount": taxable_s4, "tax": round_curr(t4)})

    # Section 87A Rebate for Old Regime (Threshold: ₹5,00,000)
    rebate_87a = 0.0
    tax_after_rebate = slab_tax

    if taxable_income <= 500000.0:
        rebate_87a = min(slab_tax, 12500.0)
        tax_after_rebate = 0.0

    cess_4_pct = tax_after_rebate * 0.04
    total_tax = tax_after_rebate + cess_4_pct

    effective_rate_pct = (total_tax / gross * 100.0) if gross > 0 else 0.0

    return {
        "regime": "OLD_TAX_REGIME",
        "legal_basis": "Income Tax Act, 1961 (Regular Slabs & Chapter VI-A)",
        "gross_income": round_curr(gross),
        "standard_deduction": round_curr(standard_deduction),
        "claimed_deductions": {
            "section_80c": round_curr(capped_80c),
            "section_80c_raw": round_curr(float(deductions_80c)),
            "section_80d": round_curr(capped_80d),
            "section_80ccd_1b_nps": round_curr(capped_80ccd1b),
            "section_24b_home_loan": round_curr(capped_24b),
            "total_deductions": round_curr(total_deductions)
        },
        "taxable_income": round_curr(taxable_income),
        "tax_before_rebate": round_curr(slab_tax),
        "rebate_87a": round_curr(rebate_87a),
        "tax_after_rebate": round_curr(tax_after_rebate),
        "cess_4_pct": round_curr(cess_4_pct),
        "total_tax": round_curr(total_tax),
        "effective_rate_pct": round(effective_rate_pct, 2),
        "slab_breakdown": slab_breakdown
    }


# ==============================================================================
# 3. STATUTORY REGIME COMPARISON & RECOMMENDATION
# ==============================================================================

def compare_tax_regimes(
    gross_income: float,
    deductions_80c: float = 0.0,
    deductions_80d: float = 0.0,
    deductions_nps_80ccd1b: float = 0.0,
    deductions_home_loan_24b: float = 0.0,
    is_salaried: bool = True
) -> Dict[str, Any]:
    """
    Compares New vs Old Tax Regime side-by-side, determines the optimal legal regime,
    and calculates tax savings.
    """
    new_tax = compute_new_regime_tax(gross_income, is_salaried=is_salaried)
    old_tax = compute_old_regime_tax(
        gross_income,
        deductions_80c=deductions_80c,
        deductions_80d=deductions_80d,
        deductions_nps_80ccd1b=deductions_nps_80ccd1b,
        deductions_home_loan_24b=deductions_home_loan_24b,
        is_salaried=is_salaried
    )

    diff = round_curr(old_tax["total_tax"] - new_tax["total_tax"])
    if diff > 0:
        recommended = "NEW_REGIME"
        savings = diff
        summary_msg = f"New Tax Regime saves you ₹{savings:,.2f} annually compared to the Old Regime."
    elif diff < 0:
        recommended = "OLD_REGIME"
        savings = abs(diff)
        summary_msg = f"Old Tax Regime saves you ₹{savings:,.2f} annually with your current deductions."
    else:
        recommended = "EQUAL"
        savings = 0.0
        summary_msg = "Both regimes yield equal tax liability."

    return {
        "recommended_regime": recommended,
        "tax_savings_amount": savings,
        "recommendation_summary": summary_msg,
        "new_regime": new_tax,
        "old_regime": old_tax
    }


# ==============================================================================
# 4. STATUTORY CAPITAL GAINS TAX (Finance Act 2024: 111A & 112A)
# ==============================================================================

def compute_capital_gains_tax(holdings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes statutory capital gains tax on holdings/realizations:
    - Equity / Equity Mutual Funds:
        - Holding period <= 365 days -> STCG (Section 111A): Taxed @ 20%
        - Holding period > 365 days  -> LTCG (Section 112A): Taxed @ 12.5%
          Statutory annual exemption: ₹1,25,000 (Finance Act 2024)
    - 4% Health & Education Cess applies to all capital gains tax
    """
    today = date.today()
    total_stcg_gain = 0.0
    total_stcg_loss = 0.0
    total_ltcg_gain = 0.0
    total_ltcg_loss = 0.0

    stcg_holdings = []
    ltcg_holdings = []

    for h in holdings:
        cost = float(h.get("total_invested", 0.0) or (float(h.get("purchase_price", 0.0)) * float(h.get("units", 1.0))))
        current = float(h.get("current_value", 0.0))
        pnl = current - cost

        buy_date_val = h.get("buy_date")
        holding_days = 0
        if buy_date_val:
            if isinstance(buy_date_val, str):
                try:
                    buy_date_obj = date.fromisoformat(buy_date_val.split("T")[0])
                    holding_days = (today - buy_date_obj).days
                except Exception:
                    holding_days = 0
            elif isinstance(buy_date_val, date):
                holding_days = (today - buy_date_val).days

        is_ltcg = holding_days > 365
        holding_summary = {
            "name": h.get("name", "Asset"),
            "symbol": h.get("symbol", ""),
            "asset_class": h.get("asset_class", "EQUITY"),
            "invested": round_curr(cost),
            "current_value": round_curr(current),
            "pnl": round_curr(pnl),
            "holding_days": holding_days,
            "classification": "LTCG" if is_ltcg else "STCG"
        }

        if is_ltcg:
            ltcg_holdings.append(holding_summary)
            if pnl > 0:
                total_ltcg_gain += pnl
            else:
                total_ltcg_loss += abs(pnl)
        else:
            stcg_holdings.append(holding_summary)
            if pnl > 0:
                total_stcg_gain += pnl
            else:
                total_stcg_loss += abs(pnl)

    # Net short term and long term gains (loss setoff within head)
    net_stcg = max(0.0, total_stcg_gain - total_stcg_loss)
    net_ltcg = max(0.0, total_ltcg_gain - total_ltcg_loss)

    # Statutory Exemption for LTCG u/s 112A = ₹1,25,000 (Finance Act 2024)
    statutory_ltcg_exemption_limit = 125000.0
    taxable_ltcg = max(0.0, net_ltcg - statutory_ltcg_exemption_limit)
    exempt_ltcg = min(net_ltcg, statutory_ltcg_exemption_limit)

    # Tax computation
    # STCG @ 20%
    stcg_tax_base = net_stcg * 0.20
    # LTCG @ 12.5% on excess above ₹1,25,000
    ltcg_tax_base = taxable_ltcg * 0.125

    cess = (stcg_tax_base + ltcg_tax_base) * 0.04
    total_tax = stcg_tax_base + ltcg_tax_base + cess

    return {
        "legal_basis": "Finance Act 2024 (Section 111A @ 20%, Section 112A @ 12.5%)",
        "stcg": {
            "gross_gain": round_curr(total_stcg_gain),
            "gross_loss": round_curr(total_stcg_loss),
            "net_gain": round_curr(net_stcg),
            "statutory_rate_pct": 20.0,
            "tax": round_curr(stcg_tax_base)
        },
        "ltcg": {
            "gross_gain": round_curr(total_ltcg_gain),
            "gross_loss": round_curr(total_ltcg_loss),
            "net_gain": round_curr(net_ltcg),
            "statutory_exemption_limit": round_curr(statutory_ltcg_exemption_limit),
            "exempt_gain": round_curr(exempt_ltcg),
            "taxable_gain": round_curr(taxable_ltcg),
            "statutory_rate_pct": 12.5,
            "tax": round_curr(ltcg_tax_base)
        },
        "health_cess_4_pct": round_curr(cess),
        "total_capital_gains_tax": round_curr(total_tax),
        "holdings_count": len(holdings),
        "stcg_holdings": stcg_holdings,
        "ltcg_holdings": ltcg_holdings
    }
