import pytest
from datetime import date, timedelta
from decimal import Decimal
from app.services.tax_engine import (
    compute_new_regime_tax,
    compute_old_regime_tax,
    compare_tax_regimes,
    compute_capital_gains_tax
)
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.investment import Investment
from app.models.category import Category


class TestNewTaxRegimeFinanceAct2024:
    """Validates Finance Act 2024 (Section 115BAC) legal tax slabs and deductions."""

    def test_zero_income(self):
        res = compute_new_regime_tax(0.0)
        assert res["gross_income"] == 0.0
        assert res["taxable_income"] == 0.0
        assert res["total_tax"] == 0.0

    def test_income_within_standard_deduction(self):
        # Gross ₹75,000 salaried -> taxable ₹0 -> tax ₹0
        res = compute_new_regime_tax(75000.0, is_salaried=True)
        assert res["standard_deduction"] == 75000.0
        assert res["taxable_income"] == 0.0
        assert res["total_tax"] == 0.0

    def test_income_within_nil_slab(self):
        # Gross ₹3,00,000 salaried -> taxable ₹2,25,000 -> tax ₹0
        res = compute_new_regime_tax(300000.0, is_salaried=True)
        assert res["taxable_income"] == 225000.0
        assert res["total_tax"] == 0.0

    def test_income_below_7_lakh_rebate_limit(self):
        # Gross ₹5,00,000 salaried -> taxable ₹4,25,000
        # Slab tax: 5% of (4,25,000 - 3,00,000) = ₹6,250
        # Rebate u/s 87A = ₹6,250 -> Net tax = ₹0
        res = compute_new_regime_tax(500000.0, is_salaried=True)
        assert res["taxable_income"] == 425000.0
        assert res["tax_before_rebate"] == 6250.0
        assert res["rebate_87a"] == 6250.0
        assert res["total_tax"] == 0.0

    def test_salary_7_75_lakh_cliff_full_rebate(self):
        # Gross ₹7,75,000 salaried -> taxable ₹7,00,000
        # Slab tax: 5% on ₹4,00,000 = ₹20,000
        # Rebate u/s 87A: Full ₹20,000 rebate!
        # Total tax = ₹0!
        res = compute_new_regime_tax(775000.0, is_salaried=True)
        assert res["taxable_income"] == 700000.0
        assert res["tax_before_rebate"] == 20000.0
        assert res["rebate_87a"] == 20000.0
        assert res["total_tax"] == 0.0

    def test_marginal_relief_section_87a(self):
        # Taxable income ₹7,05,000 (Gross ₹7,80,000 salaried)
        # Normal slab tax: ₹20,000 + 10% on ₹5,000 = ₹20,500
        # Excess over ₹7,00,000 = ₹5,000
        # Marginal relief caps tax at ₹5,000 + 4% cess = ₹5,200
        res = compute_new_regime_tax(780000.0, is_salaried=True)
        assert res["taxable_income"] == 705000.0
        assert res["tax_before_rebate"] == 20500.0
        assert res["marginal_relief_87a"] == 15500.0
        assert res["tax_after_rebate"] == 5000.0
        assert res["cess_4_pct"] == 200.0
        assert res["total_tax"] == 5200.0

    def test_ten_lakh_income(self):
        # Gross ₹10,00,000 salaried -> taxable ₹9,25,000
        # Slab 1 (0-3L): ₹0
        # Slab 2 (3L-7L): 5% of 4L = ₹20,000
        # Slab 3 (7L-9.25L): 10% of 2.25L = ₹22,500
        # Tax before rebate = ₹42,500
        # Cess 4% = ₹1,700
        # Total tax = ₹44,200
        res = compute_new_regime_tax(1000000.0, is_salaried=True)
        assert res["taxable_income"] == 925000.0
        assert res["tax_before_rebate"] == 42500.0
        assert res["cess_4_pct"] == 1700.0
        assert res["total_tax"] == 44200.0

    def test_fifteen_lakh_income(self):
        # Gross ₹15,00,000 salaried -> taxable ₹14,25,000
        # Slabs:
        # 3L-7L @ 5% = ₹20,000
        # 7L-10L @ 10% = ₹30,000
        # 10L-12L @ 15% = ₹30,000
        # 12L-14.25L @ 20% = ₹45,000
        # Tax before cess = ₹1,25,000
        # Cess 4% = ₹5,000
        # Total tax = ₹1,30,000
        res = compute_new_regime_tax(1500000.0, is_salaried=True)
        assert res["taxable_income"] == 1425000.0
        assert res["tax_before_rebate"] == 125000.0
        assert res["cess_4_pct"] == 5000.0
        assert res["total_tax"] == 130000.0


class TestOldTaxRegimeStatutoryCaps:
    """Validates Old Tax Regime with strictly enforced statutory deduction limits."""

    def test_section_80c_hard_cap_150000(self):
        # Even if user spent ₹3,00,000 in 80C, it MUST cap strictly at ₹1,50,000
        res = compute_old_regime_tax(
            gross_income=1000000.0,
            deductions_80c=300000.0,
            is_salaried=True
        )
        assert res["claimed_deductions"]["section_80c"] == 150000.0
        assert res["claimed_deductions"]["section_80c_raw"] == 300000.0
        # Total ded = ₹50,000 (std) + ₹1,50,000 (80C) = ₹2,00,000
        assert res["taxable_income"] == 800000.0

    def test_section_80d_and_nps_caps(self):
        # 80D capped at ₹25,000, 80CCD(1B) NPS capped at ₹50,000
        res = compute_old_regime_tax(
            gross_income=1200000.0,
            deductions_80c=150000.0,
            deductions_80d=60000.0,  # Exceeds ₹25,000
            deductions_nps_80ccd1b=100000.0,  # Exceeds ₹50,000
            is_salaried=True
        )
        assert res["claimed_deductions"]["section_80d"] == 25000.0
        assert res["claimed_deductions"]["section_80ccd_1b_nps"] == 50000.0
        # Total = 50k + 150k + 25k + 50k = 275k
        assert res["taxable_income"] == 925000.0

    def test_old_regime_rebate_87a_limit_5_lakh(self):
        # Gross ₹5,50,000 salaried -> taxable ₹5,00,000 (after 50k std ded)
        # Slab tax: 5% of 2.5L = ₹12,500
        # Full rebate u/s 87A = ₹12,500 -> Total tax = ₹0!
        res = compute_old_regime_tax(gross_income=550000.0, is_salaried=True)
        assert res["taxable_income"] == 500000.0
        assert res["rebate_87a"] == 12500.0
        assert res["total_tax"] == 0.0


class TestRegimeComparisonEngine:
    """Verifies automated optimal regime selection and tax savings calculation."""

    def test_recommends_new_regime_when_no_deductions(self):
        # ₹10,00,000 salary with no deductions:
        # New Regime: ₹44,200
        # Old Regime (only 50k std ded): taxable 9.5L -> tax = 12.5k + 90k = 102.5k + 4% = ₹1,06,600
        comp = compare_tax_regimes(gross_income=1000000.0, is_salaried=True)
        assert comp["recommended_regime"] == "NEW_REGIME"
        assert comp["new_regime"]["total_tax"] < comp["old_regime"]["total_tax"]
        assert comp["tax_savings_amount"] == 106600.0 - 44200.0

    def test_recommends_old_regime_when_heavy_deductions(self):
        # ₹8,00,000 salary with max 80C (1.5L), 80D (25k), NPS (50k):
        # Total ded = 50k + 150k + 25k + 50k = 275k -> Taxable = ₹5,25,000
        # Old tax: 12.5k + (25k * 20% = 5k) = 17.5k + 4% = ₹18,200
        # New tax: 8L - 75k = 7.25L -> 20k + 2.5k = 22.5k + 4% = ₹23,400
        comp = compare_tax_regimes(
            gross_income=800000.0,
            deductions_80c=150000.0,
            deductions_80d=25000.0,
            deductions_nps_80ccd1b=50000.0,
            is_salaried=True
        )
        assert comp["recommended_regime"] == "OLD_REGIME"
        assert comp["tax_savings_amount"] == 23400.0 - 18200.0


class TestStatutoryCapitalGainsTax:
    """Validates Finance Act 2024: STCG @ 20% u/s 111A, LTCG @ 12.5% u/s 112A with ₹1.25L exemption."""

    def test_stcg_only_holding_less_than_365_days(self):
        holdings = [
            {
                "name": "Tata Motors",
                "units": 100,
                "purchase_price": 500.0,
                "current_value": 70000.0,  # Gain = ₹20,000
                "buy_date": (date.today() - timedelta(days=90)).isoformat()
            }
        ]
        res = compute_capital_gains_tax(holdings)
        assert res["stcg"]["net_gain"] == 20000.0
        assert res["stcg"]["statutory_rate_pct"] == 20.0
        # Tax = 20,000 * 20% = 4,000 + 4% cess = ₹4,160
        assert res["stcg"]["tax"] == 4000.0
        assert res["total_capital_gains_tax"] == 4160.0

    def test_ltcg_below_statutory_exemption_125000(self):
        # Holding > 365 days, gain ₹1,00,000 (under ₹1,25,000 exemption)
        holdings = [
            {
                "name": "Nifty 50 Index Fund",
                "total_invested": 200000.0,
                "current_value": 300000.0,  # Gain = ₹1,00,000
                "buy_date": (date.today() - timedelta(days=500)).isoformat()
            }
        ]
        res = compute_capital_gains_tax(holdings)
        assert res["ltcg"]["net_gain"] == 100000.0
        assert res["ltcg"]["exempt_gain"] == 100000.0
        assert res["ltcg"]["taxable_gain"] == 0.0
        assert res["ltcg"]["tax"] == 0.0
        assert res["total_capital_gains_tax"] == 0.0

    def test_ltcg_exceeding_statutory_exemption_125000(self):
        # Holding > 365 days, gain ₹2,25,000
        # Exempt = ₹1,25,000
        # Taxable = ₹1,00,000
        # Tax = 1,00,000 * 12.5% = ₹12,500 + 4% cess = ₹13,000
        holdings = [
            {
                "name": "Parag Parikh Flexi Cap",
                "total_invested": 500000.0,
                "current_value": 725000.0,  # Gain = ₹2,25,000
                "buy_date": (date.today() - timedelta(days=600)).isoformat()
            }
        ]
        res = compute_capital_gains_tax(holdings)
        assert res["ltcg"]["net_gain"] == 225000.0
        assert res["ltcg"]["statutory_exemption_limit"] == 125000.0
        assert res["ltcg"]["exempt_gain"] == 125000.0
        assert res["ltcg"]["taxable_gain"] == 100000.0
        assert res["ltcg"]["tax"] == 12500.0
        assert res["health_cess_4_pct"] == 500.0
        assert res["total_capital_gains_tax"] == 13000.0

    def test_combined_portfolio_stcg_and_ltcg(self):
        holdings = [
            # STCG: Gain ₹50,000 @ 20% = ₹10,000
            {"name": "Infosys", "total_invested": 100000.0, "current_value": 150000.0, "buy_date": (date.today() - timedelta(days=120)).isoformat()},
            # LTCG: Gain ₹2,00,000. Exempt ₹1,25,000 -> Taxable ₹75,000 @ 12.5% = ₹9,375
            {"name": "HDFC Bank", "total_invested": 200000.0, "current_value": 400000.0, "buy_date": (date.today() - timedelta(days=400)).isoformat()}
        ]
        res = compute_capital_gains_tax(holdings)
        assert res["stcg"]["tax"] == 10000.0
        assert res["ltcg"]["tax"] == 9375.0
        # Base tax = 19,375. Cess = 775. Total = 20,150.
        assert res["total_capital_gains_tax"] == 20150.0


class TestApiEndpointsStatutoryTaxIntegration:
    """Verifies that API router endpoints accurately provide statutory tax data."""

    def test_reports_fy_endpoint_returns_statutory_tax_computation(self, client, db):
        # Create an account and income transaction
        acc = Account(user_id=1, name="Tax Test Account", current_balance=50000.0, account_type="SAVINGS")
        db.add(acc)
        db.commit()
        db.refresh(acc)

        tx = Transaction(
            date=date(2024, 7, 15),
            amount=Decimal("800000.00"),
            type="INCOME",
            account_id=acc.id,
            description="Annual Salary Bonus"
        )
        db.add(tx)
        db.commit()

        res = client.get("/reports/financial-year/FY 2024-25")
        assert res.status_code == 200
        data = res.json()
        assert "statutory_tax_computation" in data
        assert "statutory_capped_80c_deduction" in data
        tax_comp = data["statutory_tax_computation"]
        assert tax_comp["recommended_regime"] in ["NEW_REGIME", "OLD_REGIME", "EQUAL"]
        assert "new_regime" in tax_comp
        assert "old_regime" in tax_comp
        assert tax_comp["new_regime"]["legal_basis"] == "Finance Act 2024 (Section 115BAC)"

    def test_investments_analysis_returns_capital_gains(self, client, db):
        res = client.get("/investments/analysis")
        assert res.status_code == 200
        data = res.json()
        assert "capital_gains_tax" in data
        cg = data["capital_gains_tax"]
        assert "stcg" in cg
        assert "ltcg" in cg
        assert cg["ltcg"]["statutory_exemption_limit"] == 125000.0
        assert cg["stcg"]["statutory_rate_pct"] == 20.0
        assert cg["ltcg"]["statutory_rate_pct"] == 12.5

    def test_sips_projection_returns_statutory_ltcg(self, client):
        res = client.get("/sips/projection?monthly_amount=10000&expected_cagr_pct=15&years=5")
        assert res.status_code == 200
        data = res.json()
        assert "statutory_capital_gains_projection" in data
        proj = data["statutory_capital_gains_projection"]
        assert proj["statutory_exemption_limit"] == 125000.0
        assert proj["post_tax_future_value"] <= data["future_value"]
