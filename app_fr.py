import numpy as np
import pandas as pd
import sys
import math
from CPR import main
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from PIL import Image

# FRENCH VERSION

def write():
    #########################################
    # DEFINE FUNCTIONS USED IN SCRIPT BELOW #
    # (functions need to be defined         #
    # before script)                        #
    #########################################
    # slider to change assets returns
    def change_mean_returns(mean_returns):
        translate_returns = {'mu_equity': 'les actions',
                             'mu_bills': 'les obligations à court terme (bills)',
                             'mu_bonds': 'les obligations à long terme (bonds)',
                             'mu_housing': "l'immobilier",
                             'mu_business': "les entreprises détenues en propre"}
        st.markdown("# Hypothèses&nbsp;financières")
        st.markdown("Utiliser les [hypothèses par défaut](https://ire.hec.ca/wp-content/uploads/2021/05/assumptions-fr.pdf) concernant les rendements futurs sur les actifs / placements?")
        keep_returns = st.radio("", ["Oui", "Non"], key='keep_returns', index=0)
        if keep_returns == 'Non':
            st.write("Moyenne à long terme...")
            
            key, val = 'mu_business', mean_returns['mu_business']
            mean_returns[key] = st.slider(
                        f'... du rendement annuel réel sur {translate_returns[key]} (en %)',
                        min_value=0.0, max_value=10.0, step=1.0,
                        key="long_term_returns_"+key[3:], value=100 * val,
                        help="Des rendements nominaux sont utilisés dans le calculateur aux fins de taxation. Nous postulons un taux d'inflation annuel futur de 2%.") / 100.0
            for key, val in mean_returns.items():
                if key not in ['mu_equity', 'mu_price_rent']:
                    mean_returns[key] = st.slider(
                        f'... du rendement annuel réel sur {translate_returns[key]} (en %)',
                        min_value=0.0, max_value=10.0, step=1.0,
                        key="long_term_returns_"+key[3:], value=100 * val) / 100.0
            
            mean_returns['mu_price_rent'] = st.slider(
                    f'... du ratio prix-loyers', min_value=0.0, max_value=30.0,
                    step=1.0, key="long_term_price_rent",
                    value=float(mean_returns['mu_price_rent']))

    def ask_hh():
        st.markdown("# Répondant")
        d_hh = info_spouse()
        st.markdown("# Conjoint.e")
        spouse = st.radio("Avez-vous un.e conjoint.e?", ["Oui", "Non"], index=1)
        d_hh["couple"] = (spouse == "Oui")
        if d_hh["couple"]:
            d_hh.update(info_spouse("second"))

        fin_accs = ["rrsp", "tfsa", "other_reg", "unreg"]
        fin_prods = ["checking", "premium", "mutual", "stocks", "bonds", "gic", "etf"]
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

        st.markdown("# Ménage")
        d_hh.update(info_hh(prod_dict))
        d_hh["weight"] = 1
        return d_hh

    def info_spouse(which='first', step_amount=100):
        d = {}
        d['byear'] = st.number_input(
            "Année de naissance", min_value=1957, max_value=2020,
            key="byear_"+which, value=1980)
            
        d_gender = {'female': 'Femme', 'male': 'Homme'}
        d['sex'] = st.radio("Sexe", options=list(d_gender.keys()),
                            format_func=lambda x: d_gender[x], key="sex_"+which, 
                            help="Utilisé pour calculer l’espérance de vie et le coût des rentes", index=1)
        female = (d['sex'] == 'female')

        age = 2020 - d['byear']
        d['ret_age'] = st.number_input("Âge de retraite prévu", min_value=age+1,
                                       key="ret_age_"+which, value=max(age + 1, 65))    
        
        d['claim_age_cpp'] = min(d['ret_age'], 70)
        st.markdown("""
            L’âge de début du <div class="tooltip">RPC<span class="tooltiptext">Régime de pensions du Canada</span></div> / <div class="tooltip">RRQ<span class="tooltiptext">Régime de rentes du Québec</span></div> est fixé à l’âge de retraite que vous avez entré ci-dessus, avec un minimum de 60 ans et un maximum de 70 ans. Les prestations de <div class="tooltip">PSV<span class="tooltiptext">Pension de Sécurité de la vieillesse</span></div> / <div class="tooltip">SRG<span class="tooltiptext">Supplément de revenu garanti</span></div> débutent à 65 ans, tandis que l’Allocation au conjoint est versée de 60 à 64&nbsp;ans inclusivement.        
            """, unsafe_allow_html=True)
        st.text("")

        d_education = {'Aucun diplôme ou certificat': 'less than high school',
                       'Diplôme d’études secondaires ou certificat d’équivalence': 'high school',
                       'Certificat ou diplôme d’une école de métiers': 'post-secondary',
                       'Certificat ou diplôme d’un collège, d’un cégep ou d’un autre établissement non universitaire (autre que les certificats ou diplômes d’une école de métiers)': 'post-secondary',
                       'Certificat ou diplôme universitaire de niveau inférieur au baccalauréat': 'university',
                       "Baccalauréat": 'university',
                       'Certificat ou diplôme universitaire de niveau supérieur au baccalauréat': 'university'}
        degree = st.selectbox("Scolarité (dernier diplôme obtenu)", list(d_education.keys()),
                              key="education_"+which, help="Utilisé pour projeter les revenus de travail")
        d['education'] = d_education[degree]
        d['init_wage'] = st.number_input(
            "Revenus de travail pour 2020 (en $)", min_value=0, step=step_amount, key="init_wage_"+which, value=60000) + 1  # avoid problems with log(0)
        if which == 'first':
            text = "Avez-vous reçu une pension en 2020?"
        elif female:
            text = f"Votre conjointe a-t-elle reçu une pension en 2020?"
        else:
            text = f"Votre conjoint a-t-il reçu une pension en 2020?"
            
        pension = st.radio(text, ["Oui", "Non"], key="pension_radio_"+which, index=1)
        if pension == "Oui":
            d['pension'] = st.number_input("Montant annuel de la pension (en $)",  min_value=0, step=step_amount, key="pension_"+which, value=0)   
        if which == 'first':
            text = "Avez-vous des épargnes ou prévoyez-vous épargner à l’avenir?"
        elif female:
            text = f"Votre conjointe a-t-elle des épargnes ou prévoit-elle épargner à l’avenir?"
        else:
            text = f"Votre conjoint a-t-il des épargnes ou prévoit-il épargner à l’avenir?"
            
        savings_plan = st.radio(text, ["Oui", "Non"], key="savings_plan_"+which, index=1)
        
        if savings_plan == "Oui":
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
            text = "Recevrez-vous une pension d’un régime à prestations déterminées (PD) de votre employeur actuel ou d’un employeur passé?"
        elif female:
            text = f"Votre conjointe recevra-t-elle une pension d’un régime à prestations déterminées (PD) de son employeur actuel ou d’un employeur passé? "
        else:
            text = f"Votre conjoint recevra-t-il une pension d’un régime à prestations déterminées (PD) de son employeur actuel ou d’un employeur passé? "
            
        db_pension = st.radio(text, ["Oui", "Non"], key="db_pension_"+which, index=1)
        if db_pension == "Oui":
            st.markdown("### Pension d'un régime PD")
            d['income_previous_db'] = st.number_input(
                "Montant annuel de la pension d’un régime PD d’employeur passé (en $), une fois à la retraite",
                min_value=0, step=step_amount, key="income_previous_db_"+which)
            d['rate_employee_db'] = st.slider(
                "Taux de cotisation d’employé du régime d’employeur PD actuel (en % du revenu de travail)", min_value=0.0,
                max_value=10.0, step=0.5, key="rate_employee_db_"+which, value=5.0) / 100
            
            # replacement rate DB
            age = 2021 - d['byear']
            years_service = st.number_input(
                'Années de service à ce jour avec cotisation au régime d’employeur PD actuel',
                min_value=0, max_value=age - 18, key='year_service_'+which, value=0,
                help="Le calculateur ajoute à ce nombre les années de service jusqu’à l’âge de retraite prévu, en présumant que la personne continuera à participer au même régime; puis multiplie le total par le taux de pension ci-dessous")
            others['perc_year_db'] = st.slider(
                'Taux de pension (en % du revenu de travail par année de service)',
                min_value=1.0, max_value=3.0, value=2.0, step=0.5, key='perc_year_db_'+which) / 100
            d['replacement_rate_db'] = min((years_service + d['ret_age'] - age) * others['perc_year_db'], 0.70)
        
        if which == 'first':
            text = "Avez-vous un régime à cotisations déterminées (CD) ou semblable avec votre employeur actuel ou un employeur passé?"
        elif female:
            text = "Votre conjointe a-t-elle un régime à cotisations déterminées (CD) ou semblable avec son employeur actuel ou un employeur passé?"
        else:
            text = "Votre conjoint a-t-il un régime à cotisations déterminées (CD) ou semblable avec son employeur actuel ou un employeur passé?"
     
        dc_pension = st.radio(text, ["Oui", "Non"], key="dc_pension_"+which, index=1)
        if dc_pension == "Oui":
            st.markdown("### Régime d'employeur CD")
            d['init_dc'] = st.number_input(
                "Solde total à la fin de 2019 (en $)", min_value=0,
                step=step_amount, value=0, key="init_dc_" + which)
            d['rate_employee_dc'] = st.slider(
                "Taux de cotisation d’employé du régime d’employeur CD actuel (en % du revenu de travail)",
                min_value=0.0, max_value=20.0, step=0.5, key="rate_employee_dc_"+which, value=5.0) / 100
            d['rate_employer_dc'] = st.slider(
                "Taux de cotisation d’employeur du régime d’employeur CD actuel (en % du revenu de travail)",
                min_value=0.0, max_value=20.0, step=0.5, key="rate_employer_dc_"+which, value=5.0) / 100
            if d['rate_employee_dc'] + d['rate_employer_dc'] > 0.18:
                st.warning("**Warning:** Tax legislation caps the combined employee-employer contribution rate at 18% of earnings")
            
        if which == 'second':
            d = {'s_' + k: v for k, v in d.items()}

        return d

    def info_hh(prod_dict, step_amount=100):
        d_others = {}
        d_prov = {"qc": "Québec", "on": "Autre (utiliser le système fiscal de l'Ontario)"}
        d_others['prov'] = st.selectbox("Dans quelle province habitez-vous?",
                                        options=list(d_prov.keys()),
                                        format_func=lambda x: d_prov[x], key="prov")
        d_others.update(mix_fee(prod_dict))
        st.markdown("### Résidence")
        translate_which = {'first': 'principale', 'second':'secondaire'}
        for which in ['first', 'second']:
            which_str = f"Possédez-vous une résidence {translate_which[which]}?"
            res = st.radio(which_str, ["Oui", "Non"], key=which, index=1)
            if res == "Oui":
                d_others.update(info_residence(which))

        st.markdown("### Entreprise")
        business = st.radio("Possédez-vous une entreprise?", ["Oui", "Non"],
                            key="business", index=1)
        if business == "Oui":
            d_others['business'] = st.number_input(
                "Valeur de l’entreprise à la fin de 2019 (en $)", min_value=0,
                step=step_amount, key="business_value")
            
            sell_business = st.radio(
                "Prévoyez-vous vendre votre entreprise au moment de la retraite?",
                ["Oui", "Non"], key="business", index=1)
            if sell_business == "Oui":
                user_options['sell_business'] = True
                d_others['price_business'] = st.number_input(
                    "Prix d’achat de l’entreprise (en $)", min_value=0,
                    step=step_amount, key="business_price")

        st.markdown("### Dettes non-hypothécaires")
        mortgage = st.radio("Avez-vous des dettes autres qu’hypothécaires?",
                            ["Oui", "Non"], key="mortgage", index=1)
        if mortgage == "Oui":
            d_others.update(debts())
        return d_others

    def debts(step_amount=100):
        debt_dict = {'Dette de carte de crédit':'credit_card',
                     'Prêt personnel':'personal_loan',
                     'Prêt étudiant':'student_loan',
                     'Prêt auto':'car_loan',
                     'Marge de crédit':'credit_line',
                     'Autre dette':'other_debt'}
        l_debts = debt_dict.values()

        debt_list = st.multiselect(
            label="Choisissez vos types de dettes",
            options=list(debt_dict.keys()), key="debt_names")

        d_debts = {}
        for i in debt_list:
            debt = debt_dict[i]
            st.markdown("### {}".format(i))
            d_debts[debt] = st.number_input(
            "Solde à la fin de 2019 (en $)", min_value=0,
            step=step_amount, key="debt_"+debt_dict[i])
            d_debts[debt + "_payment"] = st.number_input(
                "Paiement mensuel moyen en 2020 (en $)", min_value=0,
                step=step_amount, key="debt_payment_"+debt_dict[i])
            
        for key in l_debts:
            if key in d_debts and (d_debts[key] == 0):
                d_debts.pop(key, None)
                d_debts.pop(key + "_payment", None)
            
        return d_debts

    def info_residence(which, step_amount=1000):
        d_res = {}
        d_res[f'{which}_mortgage'] = st.number_input(
            "Solde hypothécaire à la fin de 2019 (en $)", min_value=0,
            step=step_amount, key="res_mortgage_"+which)
        d_res[f'{which}_mortgage_payment'] = st.number_input(
            "Paiement hypothécaire mensuel en 2020 (en $)", min_value=0,
            step=step_amount, key="res_mortgage_payment_"+which)
        
        sell = st.radio("Prévoyez-vous la vendre au moment de la retraite?",
                        ["Oui", "Non"],
                        key=which+"_sell", index=1)
        if sell == "Oui":
            user_options[f'sell_{which}_resid'] = True
            d_res[f'{which}_residence'] = st.number_input(
                "Valeur à la fin de 2019 (en $)", min_value=0,
                step=step_amount, key="res_value_"+which)
        else:
            d_res[f'{which}_residence'] = 0

        if which == 'first':
            if sell == 'Oui':
                downsize= st.radio("Prévoyez-vous réduire la taille de votre habitation au moment de la retraite?",
                                   ["Oui", "Non"],
                        key=which+"_sell", index=1)
                if downsize == 'Oui':
                    user_options['downsize'] = st.number_input(
                        "De quel pourcentage (en valeur)?", value=0, min_value=0,
                        max_value=100, step=1, key="downsizing") / 100
            d_res[f'price_{which}_residence'] = d_res[f'{which}_residence']  # doesn't matter since cap gain not taxed
        else:
            if sell == "Oui":
                d_res[f'price_{which}_residence'] = st.number_input(
                    "Prix d’achat (en $)", min_value=0, step=step_amount, key="res_buy_"+which)
            else:
                d_res[f'price_{which}_residence'] = 0


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
            d_investments["Checking or regular savings account"] = prod_dict["checking"]/total_sum
            d_investments["High interest/premium savings account"] = prod_dict["premium"]/total_sum
            d_investments["Mutual funds"] = prod_dict["mutual"]/total_sum
            d_investments["Stocks"] = prod_dict["stocks"]/total_sum
            d_investments["Bonds"] = prod_dict["bonds"]/total_sum
            d_investments["GICs"] = prod_dict["gic"]/total_sum
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
        st.markdown("### Comptes d'épargne")
        d_accounts = {'rrsp': ['REER', "Régime enregistré d'épargne-retraite (REER)"],
                      'tfsa': ['CELI', "Compte d'épargne libre d'impôt (CELI)"],
                      'other_reg':['Autres comptes enregistrés', "Autres comptes enregistrés"],
                      'unreg': ['Comptes non-enregistrés', "Comptes non-enregistrés"]}
        # d_accounts_inv = {v: k for k, v in d_accounts.items()}
        saving_plan_select = st.multiselect(
            label="Sélectionner un ou plusieurs type(s) de compte",
            options= [v[1] for v in d_accounts.values()], key="fin_acc_"+which,
            help="* Les REER incluent les REER collectifs ou d’employeur, les Régimes volontaires d’épargne-retraite (RVER) et les Régimes de pension agréés  collectifs (RPAC).\n* Les autres comptes enregistrés comprennent p.ex. les comptes de retraite immobilisés (CRI) ou la portion immobilisée d’un ancien REER collectif.")
        selected_saving_plans = [key for key, val in d_accounts.items()
                                 if val[1] in saving_plan_select]
        
        for acc in selected_saving_plans:
            short_acc_name = d_accounts[acc][0]
            st.markdown("### {}".format(short_acc_name))
            
            if which == 'first':
                text = f"Solde de vos {short_acc_name} à la fin de 2019 (en $)"
            elif female:
                text = f"Solde des {short_acc_name} de votre conjointe à la fin de 2019 (en $)"
            else:
                text = f"Soldes des {short_acc_name} de votre conjoint à la fin de 2019 (en $)"
                
            d_fin["bal_" + acc] = st.number_input(
                text, value=0, min_value=0, step=step_amount, key=f"bal_{acc}_{which}")
            
            if which == 'first':
                text = f"Fraction de vos revenus de travail que vous prévoyez épargner chaque année dans des {short_acc_name} (en %)"
            elif female:
                text = f"Fraction of her earnings she plans to save annually in her {short_acc_name} accounts (in %)"
            else:
                text = f"Fraction of his earnings he plans to save annually in his {short_acc_name} accounts (in %)"
                
            d_fin["cont_rate_" + acc] = st.number_input(
                text, value=0, min_value=0, max_value=100, step=1, key=f"cont_rate_{acc}_{which}") / 100
            
            if which == 'first':
                text = f"Montant que vous prévoyez retirer chaque année de vos {short_acc_name} avant la retraite (en $)"
            elif female:
                text = f"Amount she plans to withdraw annually from her {short_acc_name} accounts prior to retirement (in $)"
            else:
                text = f"Amount he plans to withdraw annually from his {short_acc_name} accounts prior to retirement (in $)"
            
            d_fin["withdrawal_" + acc] = st.number_input(
                text, value=0, min_value=0, step=step_amount, key=f"withdraw_{acc}_{which}")
            if acc in ["rrsp", "tfsa"]:
                d_fin["init_room_" + acc] = st.number_input(
                    f"Espace de cotisation {short_acc_name} à la fin de 2019 (en $)",
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
        d_fin_prod = {}
        total_fp = 0
        st.markdown(f"### {short_acc_name} - Produits financiers")
        fin_prods = ["checking", "premium", "mutual", "stocks", "bonds", "gic",
                     "etf"]
        fin_prods_dict = {"checking": "Compte chèques ou compte d'épargne régulier",
                          "premium": "Compte d'épargne à intérêt élevé",
                          "mutual": "Fonds communs de placement",
                          "stocks": "Actions",
                          "bonds": "Obligations",
                          "gic": "Certificats de placement garantis (CPG)",
                          "etf": "Fonds négociés en Bourse (FNB)"}
        fin_prods_rev = {v: k for k, v in fin_prods_dict.items()}
        fin_prod_list = list(fin_prods_rev.keys())
        
        if which == 'first':
            label = "Sélectionner les produits financiers que vous déteniez à la fin de 2019 (le total doit être égal au solde du compte)"
        elif female:
            label = f"Sélectionner les produits financiers que votre conjointe détenait à la fin de 2019 (le total doit être égal au solde du compte)"
        else:
            label = f"Sélectionner les produits financiers que votre conjoint détenait à la fin de 2019 (le total doit être égal au solde du compte)"
            
        fin_prod_select = st.multiselect(label= label, options=fin_prod_list,
                                         key="fin_prod_list_"+ account +"_"+which)
        if not fin_prod_select:
            st.error("Aucun produit financier sélectionné. SI AUCUN PRODUIT N’EST SÉLECTIONNÉ, une allocation par défaut sera mise en œuvre pour ce type de compte.")
        fin_prods = [fin_prods_rev[i] for i in fin_prod_select]
        for prod in fin_prods:
            d_fin_prod[account+"_"+prod] = st.number_input(
                fin_prods_dict[prod], value=0, min_value=0, max_value=balance,
                step=step_amount, key=account+"_"+prod+"_"+which)
            total_fp += d_fin_prod[account+"_"+prod]

        if total_fp != balance and len(fin_prod_select)!=0:
            st.error(f"Le montant total dans les produits financiers ({total_fp:,} $) n'est pas égal au montant dans ce type de compte ({balance:,} $)")
        return d_fin_prod

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
            st.error("Votre revenu disponible pour les dépenses avant la retraite est négatif : l’épargne ou les paiements sur les dettes sont trop élevés.")
            st.stop()
        if len(df[df["cons_after"] < cons_floor]):
            st.error("Votre revenu disponible pour les dépenses après la retraite est négatif. Cela peut être dû à : 1) un remboursement trop lent de votre hypothèque (vous pourriez essayer de vendre votre résidence au moment de la retraite); 2) une valeur trop élevée de votre loyer imputé à la retraite (vous pourriez essayer de réduire la taille de votre habitation à la retraite).")
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
        st.markdown("# Taux de remplacement") 
        st.markdown("""
            Le caractère adéquat du revenu à la retraite est souvent évalué en termes de «&nbsp;taux de remplacement de la consommation&nbsp;». Dans le cas du revenu disponible pour les dépenses (c.-à-d. net des impôts, épargnes et paiement des dettes), des seuils de 80% et 65% ont été utilisés dans le [rapport de juin 2020](https://ire.hec.ca/preparation-retraite-canadiens/) produit par l’<div class=tooltip>IRE<span class=tooltiptext>Institut sur la retraite et l’épargne</span></div>, ainsi que dans des recherches et des études de politiques antérieures. Utiliser ces seuils comme références dans les figures de résultats?
            """, unsafe_allow_html=True)
        
        keep_rri = st.radio("", ["Oui", "Non"], key='keep_rri', index=0)
        if keep_rri == "Non":
            replace_rate_cons['high'] = st.slider(
                f'Taux de remplacement élevé (en % du revenu disponible pour les dépenses avant la retraite)',
                min_value=0, max_value=100,
                step=1, key="high_replace_rate_cons", value=80)
            replace_rate_cons['low'] = st.slider(
                f'Taux de remplacement faible (en % du revenu disponible pour les dépenses avant la retraite)',
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
                        name='Moyenne des 25 réalisations<br>(ligne horizontale = écart-type)',
                        error_x=dict(type='data', array=[cons_after.std()],
                                     color='darkred', thickness=1.5, width=10),                    
                        hovertemplate=
                        '$%{x:,.0f} <br>'
                        '<extra></extra>')

        fig.update_layout(height=250, width=700,
                        title={'text': f"<b>Revenu du ménage disponible pour les dépenses après la retraite <br> (en $ de 2020, {nsim} réalisations)</b>",
                                'x': 0.5, 'xanchor': 'center', 'yanchor': 'bottom'},
                        xaxis_tickformat=",",
                        xaxis_title=f"<b>Probabilité de surpasser les taux de remplacement faible et élevé,<br>respectivement : {pr_low}% et {pr_high}%</b>",
                        xaxis_title_font_size=14,
                        xaxis_range=[cons_after.min()-500, cons_after.max()+500],
                        yaxis=dict(range=[0, 2], visible= False, showticklabels=False),
                        font=dict(size=14, color="Black"),
                        legend={'traceorder':'reversed'})
        
        st.plotly_chart(fig)

        with st.beta_expander("COMMENT LIRE CETTE FIGURE"):
            st.markdown("""
                * Cette figure montre 25 « réalisations », ou possibilités, quant au revenu disponible pour les dépenses après la retraite, avec leur moyenne.
                * Les variations du revenu disponible pour les dépenses sont causées par les processus stochastiques de projection des revenus de travail et des rendements sur les actifs / placements.
                * Il n’y a pas d’axe vertical dans cette figure; les écarts verticaux sont artificiels et visent à empêcher les points de trop se superposer.""",
                unsafe_allow_html=True)

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
        names = ['Scénario principal', 'Cotisation REER +5%', 'Cotisation REER +10%',
                 'Âge retraite -2 ans', 'Âge retraite +2 ans']
        init_cons_bef, init_cons_after = \
            df_change.loc[0, ['cons_bef', 'cons_after']].values.squeeze().tolist()

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
                            'Avant la retraite: $%{x:,.0f} <br>'+
                            'Après la retraite: $%{y:,.0f} <br>'+
                            '<extra></extra>',
                            text = [f'<b>{names[index]}</b> <br />Taux de remplacement = {rri:.0f}%'],
                            showlegend = True)

        cons_bef = np.array([min(l_cons_bef) - 1000, 
                             max(l_cons_bef) + 1000]) # - 1000/+1000 for case min = max
        
        fig.add_trace(go.Scatter(
            x=cons_bef, y=replace_rate_cons['high'] / 100 * cons_bef,
            mode='lines', name=f"Taux de remplacement = {replace_rate_cons['high']}%",
            line=dict(color="RoyalBlue", width=2, dash='dash')))
        fig.add_trace(go.Scatter(
            x=cons_bef, y=replace_rate_cons['low'] / 100 * cons_bef, mode='lines',
            name=f"Taux de remplacement = {replace_rate_cons['low']}%",
            line=dict(color="Green", width=2, dash='dot')))

        fig.update_layout(height=500, width=700,
                        title={'text': f"<b>Revenu du ménage disponible pour les dépenses avant et après la retraite<br>selon différents scénarios (en $ de 2020)</b>",
                                'x': 0.5,
                                'xanchor': 'center',
                                'yanchor': 'top'},
                        xaxis_title=f"Avant la retraite<br>(année dans laquelle le répondant a {age_respondent} ans)",
                        xaxis_tickformat=",",
                        yaxis_title="Après la retraite",
                        yaxis_tickformat=",",
                        font=dict(size=14, color="Black"))
        st.text("")
        st.text("")
        st.text("")
        st.text("")
        st.plotly_chart(fig)
        with st.beta_expander("COMMENT LIRE CETTE FIGURE"):
            st.markdown("""
                * Cette figure montre le revenu disponible pour les dépenses du ménage avant et après la retraite, pour la réalisation principale des processus stochastiques pour les revenus de travail et les rendements sur les actifs / placements (le cas déterministe – qui diffère de la moyenne des 25 réalisations de la Figure 1). « Avant la retraite » réfère à l’année où le premier conjoint à prendre sa retraite a 55 ans, ou l’année avant sa retraite si celle-ci survient plus tôt – mais cette année ne peut jamais être antérieure à 2020. « Après la retraite » réfère à l’année dans laquelle le dernier conjoint à prendre sa retraite a 65 ans, ou l’année de sa retraite  si celle-ci survient plus tard.
                * Les deux lignes pointillées montrent où les points se situeraient pour les deux « taux de remplacement ».
                * Les 4 autres points montrés dans la figure illustrent l’effet de stratégies alternatives pour vous :
                    * cotiser à un <div class="tooltip">REER<span class="tooltiptext">« Régime enregistré d’épargne retraite »</span></div> 5% de votre revenu de travail de plus que ce que vous avez indiqué;
                    * cotiser à un <div class="tooltip">REER<span class="tooltiptext">« Régime enregistré d’épargne retraite »</span></div> 10% de votre revenu de travail de plus que ce que vous avez indiqué;
                    * prendre votre retraite 2 ans plus tôt que ce que vous avez indiqué;
                    * prendre votre retraite 2 ans plus tard que ce que vous avez indiqué.
                    """, unsafe_allow_html=True) 

        # RETIREMENT INCOME DISTRIBUTION
        # prepare data
        hhold = df_change.loc[0, :]
        pension = hhold['pension_after']
        annuity = (hhold['annuity_rrsp_after'] + hhold['annuity_rpp_dc_after'] 
                   + hhold['annuity_non_rrsp_after'])
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
            annuity += (hhold['s_annuity_rrsp_after']
                        + hhold['s_annuity_rpp_dc_after']
                        + hhold['s_annuity_non_rrsp_after'])
            cpp += hhold['s_cpp_after']
            gis += hhold['s_gis_after']
            oas += hhold['s_oas_after']
            allow_couple += hhold['s_allow_couple_after']
            allow_surv += hhold['s_allow_surv_after']
            rpp_db += hhold['s_rpp_db_benefits_after']
            business_dividends += hhold['s_business_dividends_after']
        income = oas + gis + cpp + rpp_db + annuity + pension

        label = ['', # 0
                'PSV', 'SRG', 'Allocation au conjoint', 'Allocation au survivant',
                'RPC/RRQ', 'Pension future d’un régime PD', 'Rente viagère', 
                'Pension actuelle', 'Dividendes d’entreprise', # 1 to 9
                'Revenu disponible pour les dépenses', 'Loyer imputé', 'Paiements sur les dettes', # 10 - 12
                "Facture d'impôts nette"]  # 13 could also enter income (invert source and target)

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
            title={'text': f"<b>Décomposition du revenu de retraite du ménage<br>(en $ de 2020)</b>",
                   'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'},
            xaxis_title="Avant la retraite", xaxis_tickformat=",",
            yaxis_title="Après la retraite", yaxis_tickformat=",",
            font=dict(size=14, color="Black"))

        st.text("")
        st.text("")
        st.text("")
        st.text("")
        st.plotly_chart(fig)
        with st.beta_expander("COMMENT LIRE CETTE FIGURE"):
            st.markdown("""
                * Cette figure montre la décomposition du revenu à la retraite de votre ménage :
                    * À gauche se trouvent les différentes sources de revenu, y compris la rente viagère achetée à la retraite avec tout votre patrimoine financier; et
                    * À droite se trouvent les différents usages de ce revenu.

                * Pour les propriétaires qui choisissent de vendre leur résidence au moment de la retraite, cela inclut un « loyer imputé », pour tenir compte du fait qu’aucun loyer n’avait à être payé avant la retraite et, ainsi, rendre comparables les revenus disponibles pour les dépenses.

                * Dans certains cas, la « Facture nette d’impôts   » apparaîtra comme source de revenu car elle est négative, c.-à-d. que les crédits et déductions du ménage sont plus élevés que ses impôts à payer.

                * Les prestations d’Allocation au conjoint cesseront lorsque le bénéficiaire aura 65 ans. Celles-ci seront remplacées à partir de cet âge par des prestations semblables de PSV et de SRG.""", unsafe_allow_html=True)
            
            
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
        rsi = Image.open("app_files/IRE.png")
        st.image(rsi)   
    with logo2:
        gri = Image.open("app_files/GRI_fr.png")
        st.image(gri)

    st.markdown("<center><h1 style='font-size: 40px'>Préparation à la retraite des Canadiens (CPR)</h1></center>", unsafe_allow_html=True)
    st.text("")
    st.text("")
    col1, col2 = st.beta_columns([0.5, 0.5])
    with col1:
        with st.beta_expander("Utilisation de l'outil", expanded=True):
            st.markdown("Bienvenue dans l’interface individuelle en ligne du [calculateur CPR](https://ire.hec.ca/preparation-retraite-canadiens/), un package Python disponible en ligne gratuitement pour une utilisation en lot (pour plusieurs ménages à la fois). Cet outil s’adresse aux individus non-retraités nés en 1957 ou après. Pour utiliser l’outil, remplir les champs et cliquer sur « Montrer les figures » au bas de la page. *L’information entrée ne sera pas conservée. Elle sera transmise de façon sécuritaire à des fins de calcul uniquement. Le calculateur CPR n’aura accès à aucune information personnelle.*")

    with col2:
        with st.beta_expander("Fonctionnement de l'outil", expanded=True):
            st.markdown("""
                En utilisant de nombreux processus et hypothèses [résumés ici](https://ire.hec.ca/wp-content/uploads/2021/05/assumptions-fr.pdf) et [présentés graphiquement ici](https://ire.hec.ca/wp-content/uploads/2021/04/CPR_flow5-fr.pdf), le CPR projette dans le futur la situation financière d’un ménage, jusqu’à un âge de retraite prédéterminé pour chaque individu. À cet âge, il convertit tout le patrimoine financier (et si désiré les résidences et entreprises) en une rente viagère « actuariellement juste », à l’aide des tables de mortalité les plus récentes et des taux projetés sur les obligations. L’outil calcule le revenu disponible pour les dépenses – après paiement des dettes, épargne, impôts, et logement pour les propriétaires – *avant* et *après* la retraite, en dollars de 2020 (réels). Il fournit ensuite de l’information au sujet de la situation financière du ménage après la retraite à l’aide de figures et de probabilités.
                """, unsafe_allow_html=True)

    st.sidebar.markdown("# CONDITIONS D'UTILISATION")
    st.sidebar.markdown("""Cet outil utilise le [calculateur de Préparation à la retraite des Canadiens](https://ire.hec.ca/preparation-retraite-canadiens), disponible en libre-accès et conçu par une équipe de l’Institut sur la retraite et l’épargne à HEC Montréal, avec le soutien financier du [National Pension Hub](https://globalriskinstitute.org/national-pension-hub/) de l’[Institut du risque mondial](https://globalriskinstitute.org/).""")
    
    
    
    st.sidebar.markdown("L’outil est fourni « tel quel » et pour usage personnel uniquement, sans garantie aucune quant à son exactitude, à son caractère approprié ou exhaustif ou à toute autre qualité. Ses résultats constituent de l’information générale sur la préparation à la retraite et ne devraient pas être considérés comme des conseils financiers; on devrait obtenir du conseil financier qualifié avant de prendre toute décision financière sur la base de cet outil.")
    st.sidebar.markdown("L’utilisation de l’outil implique l’acceptation des conditions d’utilisation ci-dessus ainsi que la prise de connaissance et la compréhension de la décharge de responsabilité ci-après.")
    with st.sidebar.beta_expander("DÉCHARGE DE RESPONSABILITÉ"):
        st.markdown("L’équipe de développement ou HEC Montréal, y compris ses employés, dirigeants ou administrateurs, ne peuvent en aucun cas être tenus responsables pour tout dommage, incluant – sans s’y limiter – les dommages directs, indirects, punitifs, connexes, spéciaux ou consécutifs résultant de l’utilisation ou de l’impossibilité d’utiliser l’outil, ou d’information fournie dans le site ou de tout défaut de performance, erreur, omission, interruption, suppression, défaut, délai de fonctionnement ou de transmission, virus informatique, bris de ligne de communication, vol ou destruction ou altération de – ou accès sans autorisation à – notre système.")

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
        if st.button("METTRE À JOUR LES FIGURES", False, help="Appuyez ici pour mettre à jour les résultats des simulations"):
            st.markdown("# Résultats des simulations")
            show_plot_button(df)
            st.text("")
            st.text("")

    if st.button("MONTRER LES FIGURES (ci-dessous ou au haut de la page)", False, help="Appuyez ici pour voir les résultats des simulations"):
        with col_p2:
            st.markdown("# Résultats des simulations")
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
            "<body style='text-align: center; black: red;'>© 2021 Institut sur la retraite et l’épargne, HEC Montréal. Tous droits réservés.</body>",
            unsafe_allow_html=True)