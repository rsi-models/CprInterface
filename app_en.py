import numpy as np
import pandas as pd
import sys
import math
from CPR import main
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from PIL import Image

#########################################
# DEFINE FUNCTIONS USED IN SCRIPT BELOW #
# (functions need to be defined         #
# before script)                        #
#########################################
def write():
    # slider to change assets returns
    def change_mean_returns(mean_returns):
        st.markdown("# Financial&nbsp;assumptions")
        st.markdown("Use [default assumptions](https://ire.hec.ca/wp-content/uploads/2021/03/assumptions.pdf) regarding future asset/investment returns?")
        keep_returns = st.radio("", ["Yes", "No"], key='keep_returns', index=0)
        if keep_returns == 'No':
            st.write("Long-term mean...")
            for key, val in mean_returns.items():
                if key != 'mu_price_rent':
                    mean_returns[key] = st.slider(
                        f'... annual real return on {key[3:]} (in %)',
                        min_value=0.0, max_value=10.0,
                        step=1.0, key="long_term_returns_"+key[3:], value=100 * val,
                        help="Nominal returns are used in the simulator for taxation purposes. We assume a 2% annual future inflation rate.") / 100.0
            
            mean_returns['mu_price_rent'] = st.slider(
                    f'... price-rent ratio', min_value=0.0, max_value=30.0,
                    step=1.0, key="long_term_price_rent",
                    value=float(mean_returns['mu_price_rent']))

    def ask_hh():
        st.markdown("# Respondent")
        d_hh = info_spouse()
        st.markdown("# Spouse")
        spouse_ques = st.radio("Do you have a spouse?", ["Yes", "No"], index=1)
        d_hh["couple"] = (spouse_ques == "Yes")
        if d_hh["couple"]:
            d_hh.update(info_spouse("second"))

        fin_accs = ["rrsp", "tfsa", "other_reg", "unreg"]
        fin_prods = ["crsa", "hipsa", "mf", "stocks", "bonds", "gic", "cvplp", "isf", "etf"]
        fin_list = []
        for i in fin_accs:
            for j in fin_prods:
                fin_list.append(i + "_" + j)
                if d_hh["couple"]:
                    fin_list.append("s_" + i + "_" + j)

        fin_dict = {}
        for i in fin_list:
            if i in d_hh:
                fin_dict[i] = d_hh[i]
            else:
                fin_dict[i] = 0
        prod_dict = pd.DataFrame([fin_dict])
        prod_dict.columns = [i.split("_")[-1] for i in list(prod_dict)]
        prod_dict = prod_dict.groupby(axis=1, level=0).sum()
        prod_dict = prod_dict.transpose().to_dict()[0]

        st.markdown("# Household")
        d_hh.update(info_hh(prod_dict))
        d_hh["weight"] = 1
        return d_hh

    def info_spouse(which='first', step_amount=100):
        d = {}
        d['byear'] = st.number_input("Birth year", min_value=1957, max_value=2020,
                                     key="byear_"+which, value=1980)
            
        d_gender = {'female': 'Female', 'male': 'Male'}
        d['sex'] = st.radio("Gender", options=list(d_gender.keys()),
                            format_func=lambda x: d_gender[x], key="sex_"+which, 
                            help="Used to compute life expectancy and the cost of annuities", index=1)
        female = (d['sex'] == 'female')

        age = 2020 - d['byear']
        d['ret_age'] = st.number_input("Intended retirement age", min_value=age+1,
                                       key="ret_age_"+which, value=max(age + 1, 65))    
        
        d['claim_age_cpp'] = min(d['ret_age'], 70)
        st.markdown("""
            <div class="tooltip">CPP<span class="tooltiptext">Canada Pension Plan</span></div>
            /
            <div class="tooltip">QPP<span class="tooltiptext">Quebec Pension Plan</span></div>
            claim age is set at the retirement age you entered above, but no less than 60&nbsp;y.o. and no more than 70&nbsp;y.o. 
            <div class="tooltip">OAS<span class="tooltiptext">Old Age Security</span></div>
            /
            <div class="tooltip">GIS<span class="tooltiptext">Guaranteed Income Supplement</span></div> benefits begin at 65 y.o., while Spouse Allowance benefits are paid from 60 to 64&nbsp;y.o. inclusively.
            """, unsafe_allow_html=True)
        st.text("")

        d_education = {'No certificate, diploma or degree': 'less than high school',
                       'Secondary (high) school diploma or equivalency certificate': 'high school',
                       'Trade certificate or diploma': 'post-secondary',
                       'College, CEGEP or other non-university certificate or diploma (other than trade certificates or diplomas)': 'post-secondary',
                       'University certificate or diploma below bachelor level': 'university',
                       "Bachelor's degree": 'university',
                       'University certificate or diploma above bachelor level': 'university'}
        degree = st.selectbox("Education (highest degree obtained)", list(d_education.keys()),
                              key="education_"+which, help="Used to forecast earnings")
        d['education'] = d_education[degree]
        d['init_wage'] = st.number_input("Annual earnings for 2020 (in $)", min_value=0,
                                         step=step_amount, key="init_wage_"+which, value=60000) + 1  # avoid problems with log(0)
        if which == 'first':
            text = "Did you receive a pension in 2020?"
        elif female:
            text = f"Did she receive a pension in 2020?"
        else:
            text = f"Did he receive a pension in 2020?"
            
        pension = st.radio(text, ["Yes", "No"], key="pension_radio_"+which, index=1)
        if pension == "Yes":
            d['pension'] = st.number_input("Yearly amount of pension (in $)",  min_value=0,
                                           step=step_amount, key="pension_"+which, value=0)   
        if which == 'first':
            text = "Do you have any savings or plan to save in the future?"
        elif female:
            text = f"Does she have any savings or plans to save in the future?"
        else:
            text = f"Does he have any savings or plans to save in the future?"
            
        savings_plan = st.radio(text, ["Yes", "No"], key="savings_plan_"+which, index=1)
        
        if savings_plan == "Yes":
            if which == 'first':
                d.update(fin_accounts(which=which))
            elif female:
                d.update(fin_accounts(which=which, female=True))
            else:
                d.update(fin_accounts(which=which, female=False))
            
        else:
            d_fin_details = {key: 0 for key in ['cap_gains_unreg', 'realized_losses_unreg',
                                                 'init_room_rrsp', 'init_room_tfsa']}
            d.update(d_fin_details)
            
        if which == 'first':
            text = "Will you receive a defined-benefit (DB) pension from your current or a previous employer?"
        elif female:
            text = f"Will she receive a defined-benefit (DB) pension from her current or a previous employer?"
        else:
            text = f"Will he receive a defined-benefit (DB) pension from his current or a previous employer?"
            
        db_pension = st.radio(text, ["Yes", "No"], key="db_pension_"+which, index=1)
        if db_pension == "Yes":
            st.markdown("### DB Pension")
            d['income_previous_db'] = st.number_input(
                "Yearly amount of DB pension from previous employer (in $), once in retirement",
                min_value=0, step=step_amount, key="income_previous_db_"+which)
            d['rate_employee_db'] = st.slider(
                "Employee contribution rate of current DB employer plan (in % of earnings)", min_value=0.0,
                max_value=10.0, step=0.5, key="rate_employee_db_"+which, value=5.0) / 100
            
            # replacement rate DB
            age = 2021 - d['byear']
            years_service = st.number_input(
                'Years of service to date contributing to current DB employer plan',
                min_value=0, max_value=age - 18, key='year_service_'+which, value=0,
                help="The simulator adds to this number the years of service until your retirement age, assuming you will keep participating in the same plan, and multiplies this by the pension rate below")
            others['perc_year_db'] = st.slider(
                'Pension rate (in % of earnings per year of service)',
                min_value=1.0, max_value=3.0, value=2.0, step=0.5, key='perc_year_db_'+which) / 100
            d['replacement_rate_db'] = min((years_service + d['ret_age'] - age) * others['perc_year_db'], 0.70)
        
        if which == 'first':
            text = "Do you have a defined-contribution (DC) or similar pension plan from your current or a previous employer?"
        elif female:
            text = "Does she have a defined-contribution (DC) or similar pension plan from her current or a previous employer?"
        else:
            text = "Does he have a defined-contribution (DC) or similar pension plan from his current or a previous employer?"
     
        dc_pension = st.radio(text, ["Yes", "No"], key="dc_pension_"+which, index=1)
        if dc_pension == "Yes":
            st.markdown("### DC employer plan")
            d['init_dc'] = st.number_input(
                "Total balance at the end of 2019 (in $)", min_value=0,
                step=step_amount, value=0, key="init_dc_" + which)
            d['rate_employee_dc'] = st.slider(
                "Employee contribution rate of current DC employer plan (in % of earnings)",
                min_value=0.0, max_value=20.0, step=0.5, key="rate_employee_dc_"+which, value=5.0) / 100
            d['rate_employer_dc'] = st.slider(
                "Employer contribution rate of current DC employer plan (in % of earnings)",
                min_value=0.0, max_value=20.0, step=0.5, key="rate_employer_dc_"+which, value=5.0) / 100
            if d['rate_employee_dc'] + d['rate_employer_dc'] > 0.18:
                st.warning("**Warning:** Tax legislation caps the combined employee-employer contribution rate at 18% of earnings")
            
        if which == 'second':
            d = {'s_' + k: v for k, v in d.items()}

        return d

    def info_hh(prod_dict, step_amount=100):
        d_others = {}
        d_prov = {"qc": "Quebec", "on": "Other (using the Ontario tax system)"}
        d_others['prov'] = st.selectbox("Which province do you live in?",
                                        options=list(d_prov.keys()),
                                        format_func=lambda x: d_prov[x], key="prov")
        d_others.update(mix_fee(prod_dict))
        st.markdown("### Residences")
        for which in ['first', 'second']:
            which_str = "Do you own a " + which + " residence?"
            res = st.radio(which_str, ["Yes", "No"], key=which, index=1)
            if res == "Yes":
                d_others.update(info_residence(which))

        st.markdown("### Business")
        business = st.radio("Do you own a business?", ["Yes", "No"], key="business", index=1)
        if business == "Yes":
            d_others['business'] = st.number_input(
                "Value of the business at the end of 2019 (in $)", min_value=0,
                step=step_amount, key="business_value")
            
            sell_business = st.radio("Do you plan to sell your business upon retirement?",
                     ["Yes", "No"], key="business", index=1)
            if sell_business == 'Yes':
                user_options['sell_business'] = True
                d_others['price_business'] = st.number_input(
                    "Buying price of the business (in $)", min_value=0, step=step_amount,
                    key="business_price")

        st.markdown("### Debts other than mortgage")
        mortgage = st.radio("Do you have any debt other than mortgage?",
                            ["Yes", "No"], key="mortgage", index=1)
        if mortgage == "Yes":
            d_others.update(debts())
        return d_others

    def debts(step_amount=100):
        debt_dict = {'Credit card debt':'credit_card',
                     'Personal loan':'personal_loan',
                     'Student loan':'student_loan',
                     'Car loan':'car_loan',
                     'Credit line':'credit_line',
                     'Other debt':'other_debt'}
        l_debts = debt_dict.values()

        debt_list = st.multiselect(label="Select your debt types", options=list(debt_dict.keys()), key="debt_names") #addition

        d_debts = {}
        for i in debt_list:
            debt = debt_dict[i]
            st.markdown("### {}".format(i))
            d_debts[debt] = st.number_input(
            "Outstanding balance at the end of 2019 (in $)", min_value=0,
            step=step_amount, key="debt_"+debt_dict[i])
            d_debts[debt + "_payment"] = st.number_input(
                "Monthly payment (in $)", min_value=0, step=step_amount,
                key="debt_payment_"+debt_dict[i])
            
        for key in l_debts: #addition
            if key in d_debts and (d_debts[key] == 0):
                d_debts.pop(key, None)
                d_debts.pop(key + "_payment", None)
            
        return d_debts

    def info_residence(which, step_amount=1000):
        d_res = {}
        res = "the " + which + " residence"
        sell = st.radio("Do you plan to sell it upon retirement?", ["Yes", "No"],
                        key=which+"_sell", index=1)
        if sell == "Yes":
            user_options[f'sell_{which}_resid'] = True
            d_res[f'{which}_residence'] = st.number_input(
                "Value at the end of 2019 (in $)", min_value=0,
                step=step_amount, key="res_value_"+which)
        else:
            d_res[f'{which}_residence'] = 0

        if which == 'first':
            if sell == 'Yes':
                downsize= st.radio("Do you plan to downsize upon retirement?", ["Yes", "No"],
                        key=which+"_sell", index=1)
                if downsize == 'Yes':
                    user_options['downsize'] = st.number_input(
                        "By what percentage (in value) do you plan to downsize?", value=0, min_value=0,
                        max_value=100, step=1, key="downsizing") / 100
            d_res[f'price_{which}_residence'] = d_res[f'{which}_residence']  # doesn't matter since cap gain not taxed
        else:
            if sell == "Yes":
                d_res[f'price_{which}_residence'] = st.number_input(
                    "Buying price (in $)", min_value=0, step=step_amount, key="res_buy_"+which)
            else:
                d_res[f'price_{which}_residence'] = 0

        d_res[f'{which}_mortgage'] = st.number_input(
            "Outstanding mortgage at the end of 2019 (in $)", min_value=0, step=step_amount,
            key="res_mortgage_"+which)
        d_res[f'{which}_mortgage_payment'] = st.number_input(
            "Monthly payment on mortgage in 2020 (in $)", min_value=0, step=step_amount,
            key="res_mortgage_payment_"+which)
        return d_res

    def mix_fee(prod_dict):
        df = pd.read_csv('app_files/mix_fee_assets.csv', index_col=0, usecols=range(0, 5))
        d_investments = {}
        total_sum = sum(prod_dict.values())
        # portfolio for people without current savings (loosely calibrated from PowerCorp's database)
        if total_sum == 0:
            d_mix_fee = {}
            d_mix_fee['fee_equity'] = 0.005
            d_mix_fee["mix_bills"] = 0.60
            d_mix_fee["mix_bonds"] = 0.15
            d_mix_fee["mix_equity"] = 0.25
            d_mix_fee["fee"] = 0.015
            
        else:
            d_investments["Checking or regular savings account"] = prod_dict["crsa"]/total_sum
            d_investments["High interest/premium savings account"] = prod_dict["hipsa"]/total_sum
            d_investments["Mutual funds"] = prod_dict["mf"]/total_sum
            d_investments["Stocks"] = prod_dict["stocks"]/total_sum
            d_investments["Bonds"] = prod_dict["bonds"]/total_sum
            d_investments["GICs"] = prod_dict["gic"]/total_sum
            d_investments["Cash value of permanent life policy"] = prod_dict["cvplp"]/total_sum
            d_investments["Individual segregated funds"] = prod_dict["isf"]/total_sum
            d_investments["ETFs"] = prod_dict["etf"]/total_sum
            d_mix_fee = {key: 0 for key in df.columns}
            df['fraction'] = pd.Series(d_investments)
            for key in d_mix_fee:
                d_mix_fee[key] = (df[key] * df.fraction).sum()
            if (df.equity * df.fraction).sum() == 0:
                d_mix_fee['fee_equity'] = 0
            else:
                d_mix_fee['fee_equity'] = (df.equity * df.fraction * df.fee).sum() / (df.equity * df.fraction).sum()
            if math.isnan(d_mix_fee['fee_equity']):
                d_mix_fee['fee_equity'] = 0
            d_mix_fee["mix_bills"] = d_mix_fee.pop("bills")
            d_mix_fee["mix_bonds"] = d_mix_fee.pop("bonds")
            d_mix_fee["mix_equity"] = d_mix_fee.pop("equity")
            
        return d_mix_fee

    def fin_accounts(which, step_amount=100, female=None):
        d_fin = {}
        d_fin["bal_unreg"] = 0 #default
        st.markdown("### Savings accounts")
        d_accounts = {'rrsp': ['RRSP', "Registered Retirement Savings Plans (RRSPs)"],
                      'tfsa': ['TFSA', "Tax-Free Savings Accounts (TFSAs)"],
                      'other_reg':['Other registered', "Other registered accounts"],
                      'unreg': ['Unregistered', "Unregistered accounts"]}
        # d_accounts_inv = {v: k for k, v in d_accounts.items()}
        saving_plan_select = st.multiselect(
            label="Select one or more account type(s)", options= [v[1] for v in d_accounts.values()],
            key="fin_acc_"+which)
        selected_saving_plans = [key for key, val in d_accounts.items()
                                 if val[1] in saving_plan_select]
        
        for acc in selected_saving_plans:
            short_acc_name = d_accounts[acc][0]
            st.markdown("### {}".format(short_acc_name))
            
            if which == 'first':
                text = f"Balance of your {short_acc_name} accounts at the end of 2019 (in $)"
            elif female:
                text = f"Balance of her {short_acc_name} accounts at the end of 2019 (in $)"
            else:
                text = f"Balance of his {short_acc_name} accounts at the end of 2019 (in $)"
                
            d_fin["bal_" + acc] = st.number_input(
                text, value=0, min_value=0, step=step_amount, key=f"bal_{acc}_{which}")
            
            if which == 'first':
                text = f"Fraction of your earnings you plan to save annually in your {short_acc_name} accounts (in %)"
            elif female:
                text = f"Fraction of her earnings she plans to save annually in her {short_acc_name} accounts (in %)"
            else:
                text = f"Fraction of his earnings he plans to save annually in his {short_acc_name} accounts (in %)"
                
            d_fin["cont_rate_" + acc] = st.number_input(
                text, value=0, min_value=0, max_value=100, step=1, key=f"cont_rate_{acc}_{which}") / 100
            
            if which == 'first':
                text = f"Amount you plan to withdraw annually from your {short_acc_name} accounts prior to retirement (in $)"
            elif female:
                text = f"Amount she plans to withdraw annually from her {short_acc_name} accounts prior to retirement (in $)"
            else:
                text = f"Amount he plans to withdraw annually from his {short_acc_name} accounts prior to retirement (in $)"
            
            d_fin["withdrawal_" + acc] = st.number_input(
                text, value=0, min_value=0, step=step_amount, key=f"withdraw_{acc}_{which}")
            if acc in ["rrsp", "tfsa"]:
                d_fin["init_room_" + acc] = st.number_input(
                    "{} contribution room at the end of 2019".format(short_acc_name),
                    value=0, min_value=0, step=step_amount, key=f"init_room_{acc}_{which}")

            if d_fin["bal_" + acc] > 0:
                if which == 'first':
                    d_fin.update(financial_products(acc, d_fin["bal_" + acc], which,
                                                    short_acc_name, step_amount=step_amount))
                elif female:
                    d_fin.update(financial_products(acc, d_fin["bal_" + acc], which,
                                                    short_acc_name, step_amount=step_amount,
                                                    female=True))
                else:
                    d_fin.update(financial_products(acc, d_fin["bal_" + acc], which,
                                                    short_acc_name, step_amount=step_amount,
                                                    female=False))

        if d_fin["bal_unreg"] > 0:
            st.markdown("### Gains and losses in unregistered Account")
            d_fin['cap_gains_unreg'] = st.number_input(
                "Balance of unrealized capital gains as of January 1, 2020 (in $)",
                value=0, min_value=0, step=step_amount, key="cap_gains_unreg_"+which)
            d_fin['realized_losses_unreg'] = st.number_input(
                "Realized losses in capital on unregistered account as of January 1, 2020 (in $)",
                value=0, min_value=0, step=step_amount, key="realized_losses_unreg_"+which)
        return d_fin

    def financial_products(account, balance, which, short_acc_name, step_amount=100,
                           female=None):
        d_fp = {}
        total_fp = 0
        st.markdown("### {} - Financial products".format(short_acc_name))
        fin_prods = ["crsa", "hipsa", "mf", "stocks", "bonds", "gic", "cvplp", "isf", "etf"]
        fin_prods_dict = {"crsa": "Checking or regular savings account",
                          "hipsa": "High interest/premium savings account",
                          "mf": "Mutual funds",
                          "stocks": "Stocks",
                          "bonds": "Bonds",
                          "gic": "GICs",
                          "etf": "ETFs"}

        fin_prods_rev = {v: k for k, v in fin_prods_dict.items()} #addition
        fin_prod_list = list(fin_prods_rev.keys()) #addition
        
        if which == 'first':
            label = "Select the financial products you own (total must add up to account balance)"
        elif female:
            label = f"Select the financial products she owns (total must add up to account balance)"
        else:
            label = f"Select the financial products he owns (total must add up to account balance)"
            
        fin_prod_select = st.multiselect(label= label, options=fin_prod_list,
                                         key="fin_prod_list_"+ account +"_"+which) #addition
        if not fin_prod_select:
            st.error("No financial product selected. IF NO PRODUCTS ARE SELECTED, a default allocation will be implemented for this account type.")
        fin_prods = [fin_prods_rev[i] for i in fin_prod_select] #addition
        for i in fin_prods:
            d_fp[account+"_"+i] = st.number_input(fin_prods_dict[i], value=0, min_value=0, max_value=balance,
                                                  step=step_amount, key=account+"_"+i+"_"+which)
            total_fp += d_fp[account+"_"+i]

        if total_fp != balance and len(fin_prod_select)!=0:
            st.error("Total amount in financial products ({} $) is not equal to amount in this account type ({} $)".format(
                    format(total_fp, ",d"), format(balance, ",d")))
        return d_fp

    def create_dataframe(d_hh):
        l_p = ['byear', 'sex', 'ret_age', 'education', 'init_wage', 'pension', 'bal_rrsp', 'bal_tfsa', 'bal_other_reg', 'bal_unreg',
                'cont_rate_rrsp', 'cont_rate_tfsa', 'cont_rate_other_reg', 'cont_rate_unreg', 'withdrawal_rrsp', 'withdrawal_tfsa',
                'withdrawal_other_reg', 'withdrawal_unreg', 'replacement_rate_db',
                'rate_employee_db', 'income_previous_db', 'init_dc', 'rate_employee_dc', 'rate_employer_dc', 'claim_age_cpp',
                'cap_gains_unreg', 'realized_losses_unreg', 'init_room_rrsp', 'init_room_tfsa']
        l_sp = ['s_' + var for var in l_p]
        l_hh = ['weight', 'couple', 'prov', 'first_residence', 'second_residence', 'price_first_residence', 'price_second_residence', 
                'business', 'price_business', 'mix_bonds', 'mix_bills', 'mix_equity', 'fee', 'fee_equity', 'credit_card', 
                'personal_loan', 'student_loan', 'car_loan', 'credit_line', 'first_mortgage', 'second_mortgage', 'other_debt', 
                'credit_card_payment', 'personal_loan_payment', 'student_loan_payment', 'car_loan_payment', 'credit_line_payment',
                'first_mortgage_payment', 'second_mortgage_payment', 'other_debt_payment']   
        
        return pd.DataFrame(d_hh, columns=l_p + l_sp + l_hh, index=[0])

    def check_cons_positive(df, cons_floor = 0):
        if len(df[df["cons_bef"] < cons_floor]):
            st.error("Your income available for spending before retirement is negative: savings or debt payments are too high.")
            st.stop()
        if len(df[df["cons_after"] < cons_floor]):
            st.error("Your income available for spending in retirement is negative. This may be due to: 1) your mortgage repayment being too slow (you may try selling your home upon retirement); 2) the value of your imputed rent in retirement being too high (you may try home downsizing at retirement).")
            st.stop()

    def create_data_changes(df):
        df_change = pd.DataFrame(np.repeat(df.values, 5, axis=0), columns=df.columns)
        df_change.cont_rate_rrsp += np.array([0, 0.05, 0.10, 0, 0])
        df_change.ret_age += np.array([0, 0, 0, -2, 2])
        if any(df_change.couple) is True:
            df_change.s_ret_age += np.array([0, 0, 0, -2, 2])
        return df_change

    # slider to change replacement rates      
    def change_replace_rate_cons():
        st.markdown("# Replacement rates") 
        st.markdown("The adequacy of retirement incomes is often assessed using “consumption replacement rates”. In the case of income available for spending (i.e. net of taxes, savings and debt payments), thresholds of 80% and 65% have been used in the <div class=tooltip>RSI<span class=tooltiptext>Retirement and Savings Institute</span></div>’s [June 2020 report](https://ire.hec.ca/en/canadians-preparation-retirement-cpr/) as well as in previous research and policy literature. Use these thresholds as benchmarks in the results figures?", unsafe_allow_html=True)
        
        keep_rri = st.radio("", ["Yes", "No"], key='keep_rri', index=0)
        if keep_rri == 'No':
            replace_rate_cons['high'] = st.slider(
                f'High replacement rate (in % of pre-retirement consumption)',
                min_value=0, max_value=100,
                step=1, key="high_replace_rate_cons", value=80)
            replace_rate_cons['low'] = st.slider(
                f'Low replacement rate (in % of pre-retirement consumption)',
                min_value=0, max_value=replace_rate_cons['high'],
                value=min(65, replace_rate_cons['high']),
                step=1, key="low_replace_rate_cons")


    ###########
    # FIGURES #
    ###########

    def show_plot_button(df):
        
        # STOCHASTIC RESULTS
        nsim = 25
        results = main.run_simulations(df, nsim=nsim, n_jobs=1, non_stochastic=False,
                                       base_year=2020, **others,
                                       **user_options, **returns, **mean_returns)
        df_output = results.output
        check_cons_positive(df_output, cons_floor = 0)
        df_output['RRI'] = (df_output.cons_after / df_output.cons_bef * 100).round(1)
        
        # prob prepared:
        pr_low = int(np.round(100 * (df_output['RRI'] >= replace_rate_cons['low']).mean(), 0))
        pr_high = int(np.round(100 * (df_output['RRI'] >= replace_rate_cons['high']).mean(), 0))

        # FIGURE 1: STOCHASTIC RESULTS
        fig = go.Figure()
        cons_after = df_output.cons_after
        noise = 0.2
        y = np.random.uniform(low=1-noise, high=1+noise, size=cons_after.shape)
        fig.add_scatter(x=cons_after, y=y, mode='markers',
                        marker=dict(size=12, color='blue', opacity=0.3),
                        hovertemplate=
                        '$%{x:,.0f} <br>'
                        '<extra></extra>',
                        showlegend = False)
        
        fig.add_scatter(x=[cons_after.mean()], y=[1], mode='markers',
                        marker_symbol='x',
                        marker=dict(size=15, color='darkred'),
                        name='Average of the 25 realizations<br>(horizontal line = standard deviation)',
                        error_x=dict(type='data', array=[cons_after.std()],
                                     color='darkred', thickness=1.5, width=10),                    
                        hovertemplate=
                        '$%{x:,.0f} <br>'
                        '<extra></extra>')

        fig.update_layout(height=250, width=700,
                        title={'text': f"<b>Household income available for spending after retirement <br> (in 2020 $, {nsim} realizations)</b>",
                                'x': 0.5, 'xanchor': 'center', 'yanchor': 'bottom'},
                        xaxis_tickformat=",",
                        xaxis_title=f"<b>Probability of exceeding the selected low and high replacement rates,<br>respectively: {pr_low}% and {pr_high}%</b>",
                        xaxis_title_font_size=14,
                        xaxis_range=[cons_after.min()-500, cons_after.max()+500],
                        yaxis=dict(range=[0, 2], visible= False, showticklabels=False),
                        font=dict(size=14, color="Black"),
                        legend={'traceorder':'reversed'})
        
        st.plotly_chart(fig)

        with st.beta_expander("HOW TO READ THIS FIGURE"):
            st.markdown("""
                * This figure shows 25 “realizations”, or possibilities of household income available for spending after retirement, with their average. “After retirement” is defined as the year when the the last spouse to retire is age 65, or his/her retirement year if later.
                * Variations in income available for spending are driven by the stochastic processes for earnings and asset/investment returns.
                * There is no vertical axis to the figure; the vertical differences are artificial and aim to prevent the data points from overlapping excessively.
                """, unsafe_allow_html=True)

        # CHANGES IN CONTRIBUTION RATE AND RETIREMENT AGE
        # calculations
        df_change = create_data_changes(df)
        results = main.run_simulations(df_change, nsim=1, n_jobs=1,non_stochastic=True,
                                       base_year=2020, **others,
                                       **user_options, **returns, **mean_returns)
        results.merge()
        df_change = results.df_merged
        age_respondent = df_change['year_cons_bef'][0] - d_hh['byear']
        
        # FIGURE 2: CHANGES IN CONTRIBUTION RATE RRSP AND RETIREMENT AGE
        
        names = ['Main scenario', 'RRSP contrib +5%', 'RRSP contrib +10%',
                 'Retirement age -2 years', 'Retirement age +2 years']
        init_cons_bef, init_cons_after = df_change.loc[0, ['cons_bef', 'cons_after']].values.squeeze().tolist()

        fig = go.Figure()

        l_cons_bef = []
        colors = ['darkred', 'blue', 'green', 'blue', 'green']
        symbols = ['x', 'diamond', 'diamond', 'circle', 'circle']
        sizes = [15, 12, 12, 12, 12]
        for index, row in df_change.iterrows():
            l_cons_bef.append(row['cons_bef'])
            rri = row['cons_after'] / row['cons_bef'] * 100
            fig.add_scatter(x=[row['cons_bef']], y=[row['cons_after']],
                            mode='markers',
                            marker_color=colors[index],
                            marker_symbol = symbols[index],
                            marker=dict(size=sizes[index]),
                            name=names[index],
                            hovertemplate=
                            '%{text} <br>'
                            'Before ret: $%{x:,.0f} <br>'+
                            'After ret: $%{y:,.0f} <br>'+
                            '<extra></extra>',
                            text = [f'<b>{names[index]}</b> <br />Replacement rate = {rri:.0f}%'],
                            showlegend = True)

        # cons_bef = np.array([min(l_cons_bef), max(l_cons_bef)])
        cons_bef = np.array([min(l_cons_bef) - 1000, 
                             max(l_cons_bef) + 1000]) # - 1000/+1000 for case min = max
        
        fig.add_trace(go.Scatter(
            x=cons_bef, y=replace_rate_cons['high'] / 100 * cons_bef,
            mode='lines', name=f"Replacement rate = {replace_rate_cons['high']}%",
            line=dict(color="RoyalBlue", width=2, dash='dash')))
        fig.add_trace(go.Scatter(
            x=cons_bef, y=replace_rate_cons['low'] / 100 * cons_bef, mode='lines',
            name=f"Replacement rate = {replace_rate_cons['low']}%",
            line=dict(color="Green", width=2, dash='dot')))

        fig.update_layout(height=500, width=700,
                        title={'text': f"<b>Household income available for spending before and after retirement <br> under alternative scenarios (in 2020 $)</b>",
                                'x': 0.5,
                                'xanchor': 'center',
                                'yanchor': 'top'},
                        xaxis_title=f"Before retirement<br>(year when respondent is {age_respondent} y.o.)",
                        xaxis_tickformat=",",
                        yaxis_title="After retirement",
                        yaxis_tickformat=",",
                        font=dict(size=14, color="Black"))
        st.text("")
        st.text("")
        st.text("")
        st.text("")
        st.plotly_chart(fig)
        with st.beta_expander("HOW TO READ THIS FIGURE"):
            st.markdown("""
                * This figure shows household income available for spending before retirement and after, for the main realization of the stochastic processes for earnings and asset/investment returns (the deterministic case – which differs from the mean of the 25 stochastic realizations in Figure 1). “Before retirement” is defined as the year when the first spouse to retire is age 55, or the year before he/she retires if earlier — but no sooner than 2020. “After retirement” is defined as the year when the last spouse to retire is age 65, or his/her retirement year if later.
                * The two dashed lines show where dots would lie for the two selected “replacement rates”.
                * The other 4 points shown in the figure illustrate the effect of alternative actions for you:
                    * retiring 2 years later than you indicated;
                    * retiring 2 years earlier then you indicated;
                    * contributing to an <div class="tooltip">RRSP<span class="tooltiptext">Registered Retirement Savings Plans</span></div> 5% more of your earnings than you indicated;
                    * contributing to an <div class="tooltip">RRSP<span class="tooltiptext">Registered Retirement Savings Plans</span></div> 10% more of your earnings than you indicated.""", unsafe_allow_html=True)

        # RETIREMENT INCOME DISTRIBUTION
        # prepare data
        hhold = df_change.loc[0, :]
        pension = hhold['pension_after']
        annuity = hhold['annuity_rrsp_after'] + hhold['annuity_rpp_dc_after'] + hhold['annuity_non_rrsp_after']
        consumption = hhold['cons_after']
        debt_payments = hhold['debt_payments_after']
        imputed_rent = hhold['imputed_rent_after']
        net_liabilities = hhold['fam_net_tax_liability_after']
        cpp = hhold['cpp_after']
        gis = hhold['gis_after']
        oas = hhold['oas_after']
        allow_couple = hhold['allow_couple_after']
        allow_surv = hhold['allow_surv_after']
        rpp_db = hhold['rpp_db_benefits_after']
        business_dividends = hhold['business_dividends_after']
        
        if hhold['couple']:
            pension += hhold['s_pension_after']
            annuity += hhold['s_annuity_rrsp_after'] + hhold['s_annuity_rpp_dc_after'] + hhold['s_annuity_non_rrsp_after']
            cpp += hhold['s_cpp_after']
            gis += hhold['s_gis_after']
            oas += hhold['s_oas_after']
            allow_couple += hhold['s_allow_couple_after']
            allow_surv += hhold['s_allow_surv_after']
            rpp_db += hhold['s_rpp_db_benefits_after']
            business_dividends += hhold['s_business_dividends_after']
        income = oas + gis + cpp + rpp_db + annuity + pension

        label = ['', # 0
                'OAS', 'GIS', 'Spouse Allowance', 'Allowance for the Survivor', 'CPP/QPP', 
                'Future pension from DB plan', 'Annuity', 'Current pension', 'Business dividends', # 1 to 9
                'Income available for spending', 'Imputed rent', 'Debt payments', # 10 - 12
                'Net tax liability']  # 13 could also enter income (invert source and target)

        if net_liabilities > 0:
            source = [1, 2, 3, 4, 5, 6, 7, 8, 9,  0,  0,  0,  0]
            target = [0, 0, 0, 0, 0, 0, 0, 0, 0, 10, 11, 12, 13]
            value =  [oas, gis, allow_couple, allow_surv, cpp, rpp_db, annuity, 
                      pension, business_dividends, consumption, imputed_rent,
                      debt_payments, net_liabilities]
        else:
            source = [1, 2, 3, 4, 5, 6, 7, 8, 9,  0,  0,  0, 13]
            target = [0, 0, 0, 0, 0, 0, 0, 0, 0, 10, 11, 12,  0]
            value =  [oas, gis, allow_couple, allow_surv, cpp, rpp_db, annuity,
                      pension, business_dividends, consumption, imputed_rent,
                      debt_payments, -net_liabilities]
        
        color_nodes = px.colors.qualitative.Safe[:len(source)]

        # data to dict, dict to sankey diagram
        link = dict(source = source,
                    target = target,
                    value = value,
                    hovertemplate='$%{value:,.0f}<extra></extra>')
        node = dict(label = label, pad=20, thickness=50,
                    hovertemplate='$%{value:,.0f}<extra></extra>',
                    color=color_nodes)

        data = go.Sankey(link=link, node=node)
        # plot
        fig = go.Figure(data)
        fig.update_layout(
            height=500, width=700,
            title={'text': f"<b>Household retirement income decomposition <br> (in 2020 $)</b>",
                   'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'},
            xaxis_title="Before retirement", xaxis_tickformat=",",
            yaxis_title="After retirement", yaxis_tickformat=",",
            font=dict(size=14, color="Black"))

        st.text("")
        st.text("")
        st.text("")
        st.text("")
        st.plotly_chart(fig)
        with st.beta_expander("HOW TO READ THIS FIGURE"):
            st.markdown("""
                * This figure shows the decomposition of your household’s income in retirement:
                    * on the left are the various income sources, including the annuity purchased upon retirement with all your financial wealth;
                    * and on the right are the uses of that income.
                * For homeowners who choose to sell their home at retirement, this includes a “rent equivalent”, to account for the fact that no rent had to be paid prior to retirement and make incomes available for spending comparable.
                * In certain cases, “Net tax liability” will appear as an income source because it is negative – i.e., the household has more credits and deductions than it has taxes to pay.
                * Spouse Allowance benefits will cease when the recipient turns 65. They will be replaced by similar GIS benefits at that age.""", unsafe_allow_html=True)
            
            
            ####################       
    # SCRIPT INTERFACE #
    ####################

    # parameters for 2020 instead of 2018:
    returns = {'ret_equity_2018': 0.0313,
               'ret_bills_2018': -0.0193,
               'ret_bonds_2018': -0.0129,
               'ret_housing_2018': 0.1062,
               'price_rent_2018': 20,
               'ret_business_2018': 0.0313}

    # long-term returns (can be changed by user)
    mean_returns = {'mu_equity': 0.0688,
                    'mu_bills': 0.0103,
                    'mu_bonds': 0.0253,
                    'mu_housing': 0.0161,
                    'mu_business': 0.0688,
                    'mu_price_rent': 15}

    # default options (can be changed by user)
    user_options = {'sell_business': False,
                    'sell_first_resid': False,
                    'sell_second_resid': False,
                    'downsize': 0}

    # consumption replacement rates (can be changed by user)
    replace_rate_cons = {'high': 80, 'low': 65}

    # db pension rate by default (can be changed by user)
    others = {'perc_year_db': 0.02}


    # load logos
    logo1, _, logo2 = st.beta_columns([0.2, 0.6, 0.2])
    with logo1:
        rsi = Image.open("app_files/RSI.png")
        st.image(rsi)
    with logo2:
        gri = Image.open("app_files/GRI.png")
        st.image(gri)

    st.markdown("<center><h1 style='font-size: 40px'>Canadians’ Preparation for Retirement (CPR)</h1></center>", unsafe_allow_html=True)
    st.text("")
    st.text("")
    col1, col2 = st.beta_columns([0.5, 0.5])
    with col1:
        with st.beta_expander("Use of the tool", expanded=True):
            st.markdown("Welcome to the individual online interface of [the CPR simulator](https://ire.hec.ca/en/canadians-preparation-retirement-cpr), [a freely available Python package](https://rsi-models.github.io/CPR/en/) also available for download for batch use. This tool is intended for use by individuals born in 1957 or later and not yet retired. To use the tool, fill in the fields and hit “Show figures” at the bottom of the page. *The information you enter will not be stored. Il will be transmitted securely and for calculations only. The CPR calculator will not have access to any personal information.*")

    with col2:
        with st.beta_expander("Functioning of the tool", expanded=True):
            st.markdown("""
                The <div class="tooltip">CPR<span class="tooltiptext">Canadians' Preparation for Retirement</span></div>
                projects a household’s financial situation into the future to a pre-specified age of retirement for each individual, using a number of processes and assumptions [summarized here](https://ire.hec.ca/wp-content/uploads/2021/03/assumptions.pdf) and [graphically depicted here](https://ire.hec.ca/wp-content/uploads/2021/03/CPR_flow5.pdf). At that age, it converts all financial wealth (and optionally residences and businesses) into an “actuarially fair” annuity, using the most recent life tables as well as projected bond rates. The tool computes income available for spending – after debt payments, saving, taxes, and housing for homeowners – *prior to* and *after* retirement, in 2020 (real) dollars. 
                It returns, in the form of figures and probabilities, information about the household’s post-retirement financial situation.
                """, unsafe_allow_html=True)


    st.sidebar.markdown("# TERMS OF USE")
    st.sidebar.markdown("""This tool uses the freely available [Canadians' Preparation for Retirement (CPR) calculator](https://ire.hec.ca/en/canadians-preparation-retirement-cpr), developed by a team at [HEC Montréal](https://www.hec.ca/en/)’s [Retirement and Savings Institute](https://ire.hec.ca/en/) with financial support from the [Global Risk Institute](https://globalriskinstitute.org/)’s [National Pension Hub](https://globalriskinstitute.org/national-pension-hub/).""")
    st.sidebar.markdown("The tool is provided “as is” for personal use only, without any warranty regarding its accuracy, appropriateness, completeness or any other quality. Its results are deemed to be general information on retirement preparation and should not be construed as financial advice; qualified financial advice should be sought before making any financial decision based on this tool.")
    st.sidebar.markdown("Use of the tool implies the acceptance of the foregoing terms and constitutes an acknowledgement that the disclaimer below has been read and understood.")
    with st.sidebar.beta_expander("DISCLAIMER"):
        st.markdown("Under no circumstances shall the developing team or HEC Montréal, including its employees, officers or directors, be liable for any damages, including without limitation direct, indirect, punitive, incidental, special or consequential damages that result from the use of, or inability to use, the tool or from information provided on the site or from any failure of performance, error, omission, interruption, deletion, defect, delay in operation or transmission, computer virus, communication line failure, theft or destruction or unauthorized access to, alteration of, or use of record.")

    col_p1, _, col_p2 = st.beta_columns([0.465, 0.025, 0.51])

    with col_p1:
        change_mean_returns(mean_returns)
        d_hh = ask_hh()
        df = create_dataframe(d_hh)
        df = df.fillna(0)
        
        # set all NaNs to zero
        fin_acc_cols = ['bal_rrsp', 'bal_tfsa', 'bal_other_reg', 'bal_unreg', 
                        'cont_rate_rrsp', 'cont_rate_tfsa', 'cont_rate_other_reg',
                        'cont_rate_unreg', 'withdrawal_rrsp', 'withdrawal_tfsa', 
                        'withdrawal_other_reg', 'withdrawal_unreg', 'cap_gains_unreg',
                        'realized_losses_unreg', 'init_room_rrsp', 'init_room_tfsa']
        
        if df['couple'][0]:
            s_fin_acc_cols = ['s_' + col for col in fin_acc_cols]
            fin_acc_cols += s_fin_acc_cols
        df[fin_acc_cols] = df[fin_acc_cols].fillna(0)
        change_replace_rate_cons()
        
    with col_p2:
        st.text("")
        st.text("")
        if st.button("UPDATE FIGURES", False, help="Click here to update the simulation results"):
            st.markdown("# Simulation results")
            show_plot_button(df)
            st.text("")
            st.text("")

    if st.button("SHOW FIGURES (below or at top of page)", False, help="Click here to see the simulation results"):
        with col_p2:
            st.markdown("# Simulation results")
            show_plot_button(df)
            st.text("")
            st.text("")
            
    st.text("")
    st.text("")       
    st.text("")
    st.text("")
    st.text("")
    st.text("")
    _, col, _ = st.beta_columns([0.2, 0.6, 0.2])

    with col:
        st.markdown(
        """<a style='display: block; text-align: center;' href="mailto:info.rsi@hec.ca?subject=CPR Online">Contact</a>
        """, unsafe_allow_html=True)
        st.markdown(
            "<body style='text-align: center; black: red;'>© 2021 Retirement and Savings Institute, HEC Montréal. All rights reserved.</body>",
            unsafe_allow_html=True)