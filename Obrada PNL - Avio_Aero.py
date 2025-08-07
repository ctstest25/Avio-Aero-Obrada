import streamlit as st
import pandas as pd
import datetime
import base64
import re
import pycountry # <-- NOVI IMPORT

# --- Konstante ---
VALID_TITLES = ["MR", "MRS", "CHD", "INF"]
EXPECTED_AERO_COLUMNS = ['Passenger Surname', 'Passenger Name', 'Title', 'Passport', 'Nationality', 'Pass Expire Date', 'Birthday']

# --- Konfiguracija stranice ---
st.set_page_config(page_title="Aero obrada", layout="centered")
st.title("🧭 PNL aero generator")

# --- Meni ---
opcija = st.sidebar.radio("Odaberi vrstu obrade", ["✈️ Obrada za Aero", "🛫 Obrada za Avio"])


# --------------------------------------------------
# ✈️ AERO OBRADA (.txt za aerodrom)
# --------------------------------------------------
if opcija == "✈️ Obrada za Aero":
    st.header("✈️ Aero PNL Generator")
    uploaded_file = st.file_uploader("📤 Učitaj .xlsx fajl", type="xlsx")

    # POBOLJŠANJE: Moćna funkcija za prepoznavanje državljanstva
    def get_country_code_advanced(name):
        """Koristi pycountry za pronalazak troslovnog koda države."""
        if not isinstance(name, str) or not name.strip():
            return "XXX"
        try:
            # search_fuzzy je odličan jer pronalazi zemlju čak i uz male greške ili varijacije
            country = pycountry.countries.search_fuzzy(name)
            if country:
                return country[0].alpha_3
            else:
                return "XXX"
        except Exception:
            return "XXX"

    def validate_passenger(row):
        warnings = []
        if not str(row.get('Passenger Surname', '')).strip(): warnings.append("Nedostaje prezime")
        if not str(row.get('Passenger Name', '')).strip(): warnings.append("Nedostaje ime")
        if str(row.get('Title', '')).strip().upper() not in VALID_TITLES: warnings.append("Nepoznata ili nedostajuća titula")
        passport = str(row.get('Passport', '')).strip().upper()
        if not passport or passport in ['NAN', '']: warnings.append("Nedostaje broj pasoša")
        elif not re.match(r'^[A-Z0-9]{5,10}$', passport): warnings.append("Pasoš neispravan")
        if pd.isna(pd.to_datetime(row.get('Birthday', None), errors='coerce', dayfirst=True)): warnings.append("Datum rođenja neispravan ili nedostaje")
        if pd.isna(pd.to_datetime(row.get('Pass Expire Date', None), errors='coerce', dayfirst=True)): warnings.append("Datum isteka pasoša neispravan ili nedostaje")
        nationality_code = get_country_code_advanced(str(row.get('Nationality', '')))
        if nationality_code == "XXX": warnings.append("Nedostaje ili je neprepoznata nacionalnost")
        return warnings

    def highlight_problems(row):
        styles = pd.Series(['' for _ in row.index], index=row.index)
        if not str(row.get('Passenger Surname', '')).strip(): styles['Passenger Surname'] = 'background-color: #fff1f1'
        if not str(row.get('Passenger Name', '')).strip(): styles['Passenger Name'] = 'background-color: #fff1f1'
        if str(row.get('Title', '')).strip().upper() not in VALID_TITLES: styles['Title'] = 'background-color: #fff1f1'
        passport = str(row.get('Passport', '')).strip().upper()
        if not passport or passport == 'NAN': styles['Passport'] = 'background-color: #fff1f1'
        elif not re.match(r'^[A-Z0-9]{5,10}$', passport): styles['Passport'] = 'background-color: #fffbe1'
        if pd.isna(pd.to_datetime(row.get('Birthday', None), errors='coerce', dayfirst=True)): styles['Birthday'] = 'background-color: #fff1f1'
        if pd.isna(pd.to_datetime(row.get('Pass Expire Date', None), errors='coerce', dayfirst=True)): styles['Pass Expire Date'] = 'background-color: #fff1f1'
        if get_country_code_advanced(str(row.get('Nationality', ''))) == 'XXX': styles['Nationality'] = 'background-color: #fff1f1'
        return styles

    def format_passenger(row):
        warnings = validate_passenger(row)
        surname = re.sub(r'\s+', ' ', str(row.get('Passenger Surname', '')).strip()).upper()
        name = re.sub(r'\s+', ' ', str(row.get('Passenger Name', '')).strip()).upper()
        title = str(row.get('Title', '')).strip().upper()
        full_name = f"{surname}/{name}"
        passport_number = str(row.get('Passport', '')).strip().upper()
        if not passport_number or passport_number in ['NAN', '']: passport_number = "XXXXXXX"
        
        # POBOLJŠANJE: Koristimo novu funkciju
        nationality_raw = str(row.get('Nationality', ''))
        nationality = get_country_code_advanced(nationality_raw)

        passport_expiry = pd.to_datetime(row.get('Pass Expire Date', None), errors='coerce', dayfirst=True)
        passport_expiry_str = passport_expiry.strftime('%d%b%y').upper() if pd.notna(passport_expiry) else "XXMMMXX"
        birthday = pd.to_datetime(row.get('Birthday', None), errors='coerce', dayfirst=True)
        birthday_str = birthday.strftime('%d%b%y').upper() if pd.notna(birthday) else "XXMMMXX"
        lines = []
        if title == "INF":
            lines.append(f".R/INF {full_name}")
            lines.append(f".R/DOCS HK1/P/{nationality}/{passport_number}/{nationality}/{passport_expiry_str}/")
            lines.append(f".RN/INF/{birthday_str}/{full_name}")
        elif title == "CHD":
            lines.append(f".R/1CHD 1{full_name}CHD")
            lines.append(f".R/DOCS HK1/P/{nationality}/{passport_number}/{nationality}/{passport_expiry_str}/")
            lines.append(f".RN/MR/{birthday_str}/{full_name}")
        else:
            lines.append(f"1{full_name}{title}")
            lines.append(f".R/DOCS HK1/P/{nationality}/{passport_number}/{nationality}/{passport_expiry_str}/")
            lines.append(f".RN/{title}/{birthday_str}/{full_name}")
        if warnings:
            lines.append(f"# UPOZORENJE: {', '.join(warnings)}")
        return "\n".join(lines)

    if uploaded_file:
        with st.spinner('Obrada fajla...'):
            try:
                df = pd.read_excel(uploaded_file, header=3)
                if not all(col in df.columns for col in EXPECTED_AERO_COLUMNS): raise ValueError("Kolone nisu prepoznate")
                st.success("✅ Uspješno učitan fajl (standardna struktura)!")
            except Exception as e:
                st.warning(f"⚠️ Neuspjeh u standardnoj obradi: {e}. Pokušavam rezervni format...")
                try:
                    df = pd.read_excel(uploaded_file, header=None, skiprows=3, usecols="A:H")
                    df.columns = ['Reservation', 'Passenger Surname', 'Passenger Name', 'Title', 'Nationality', 'Passport', 'Birthday', 'Pass Expire Date']
                    st.success("✅ Uspješno učitan fajl (rezervna logika)!")
                except Exception as e2:
                    st.error(f"❌ Neuspjeh u rezervnom načinu: {e2}")
                    st.stop()
            df["Upozorenja"] = df.apply(lambda r: ", ".join(validate_passenger(r)), axis=1)
            st.subheader("📊 Sažetak putnika")
            try:
                total_passengers = len(df)
                titles = df['Title'].str.strip().str.upper()
                adults = titles.isin(['MR', 'MRS']).sum()
                children = (titles == 'CHD').sum()
                infants = (titles == 'INF').sum()
                unknown = total_passengers - adults - children - infants
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Ukupno putnika", total_passengers)
                col2.metric("Odrasli", adults)
                col3.metric("Djeca (CHD)", children)
                col4.metric("Bebe (INF)", infants)
                if unknown > 0: st.warning(f"Pronađeno {unknown} putnika sa nepoznatom/neispravnom titulom.")
            except Exception: st.error("Nije moguće generisati sažetak zbog problema sa podacima.")
            st.subheader("📋 Učitani podaci")
            st.info("Polja sa greškom su obojena. Crveno označava podatak koji nedostaje, a žuto neispravan format.")
            st.dataframe(df.drop(columns=['Upozorenja']).style.apply(highlight_problems, axis=1))
            if df["Upozorenja"].str.len().max() > 0: st.warning("⚠️ Neki putnici imaju upozorenja. Provjerite ih prije slanja.")
            txt_output = "\n\n".join(df.apply(format_passenger, axis=1))
            st.subheader("📑 Generisani .txt sadržaj")
            st.text_area("Pregled sadržaja", txt_output, height=500)
            st.download_button(label="📥 Preuzmi .txt fajl", data=txt_output, file_name="aerodrom_export.txt", mime="text/plain")
    else:
        st.info("Učitaj .xlsx fajl da započneš obradu.")

# --------------------------------------------------
# 🛫 AVIO OBRADA (PNL format)
# --------------------------------------------------
elif opcija == "🛫 Obrada za Avio":
    st.header("🛫 Avio PNL Generator")
    st.markdown("Učitaj .xlsx fajl i generiši PNL .txt fajl za aviokompaniju.")
    uploaded_file = st.file_uploader("📤 Učitaj .xlsx fajl", type=["xlsx"])
    flight_info = st.text_input("✈️ Oznaka leta", value="CAI198/01JUL TZL PART1")
    flight_code = st.text_input("🛬 Šifra leta", value="-AYT025Y")
    if uploaded_file:
        with st.spinner('Obrada fajla...'):
            df_raw = pd.read_excel(uploaded_file, skiprows=4)
            df_raw = df_raw.iloc[:, 0:4]
            df_raw.columns = ["Reservation", "Title", "Surname", "Name"]
            df_raw.dropna(subset=["Surname", "Name"], inplace=True)
            st.subheader("📋 Učitani podaci")
            st.dataframe(df_raw)
            res_map = {}
            res_counter = 1
            output_lines = ["PNL", flight_info.strip(), flight_code.strip()]
            for _, row in df_raw.iterrows():
                res_raw = row["Reservation"] if pd.notna(row["Reservation"]) else f"FALI REZERVACIJA_{res_counter}"
                if res_raw not in res_map:
                    # Ispravljena logika za formatiranje broja rezervacije
                    res_map[res_raw] = f"{res_counter:05d}"
                    res_counter += 1
                res_code = res_map[res_raw]
                title = str(row["Title"]).strip().upper() if pd.notna(row["Title"]) else "FALI TITULA"
                surname = str(row["Surname"]).strip().upper()
                name = str(row["Name"]).strip().upper()
                suffix = title
                if title in ["MR", "MRS", "CHD", "INF"]:
                    suffix = title
                
                # Kreiranje osnovne linije bez razmaka ispred .L/
                line = f"1{surname}/{name}{suffix}.L/{res_code}"
                
                # Dodavanje prefixa za CHD i INF putnike bez dodatnih razmaka
                if suffix == "INF": 
                    line = f".R/INFT {surname}/{name}{suffix} .L/{res_code}"
                elif suffix == "CHD": 
                    line = f".R/1CHD {surname}/{name}{suffix} .L/{res_code}"

                output_lines.append(line)
            output_lines.append("ENDPNL")
            final_txt = "\n".join(output_lines)
            st.subheader("📄 Generisani .txt sadržaj")
            st.code(final_txt, language="text")
            date_str = datetime.datetime.now().strftime("%d%m%Y")
            file_name_avio = f"PNL_Export_{date_str}.txt"
            st.download_button(label="📥 Preuzmi .txt fajl", data=final_txt, file_name=file_name_avio, mime="text/plain")
    else:
        st.info("Učitaj .xlsx fajl da započneš obradu.")
