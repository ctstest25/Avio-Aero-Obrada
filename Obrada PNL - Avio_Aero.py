import streamlit as st
import pandas as pd
import datetime
import base64
import re

# Konfiguracija
st.set_page_config(page_title="Aero obrada", layout="centered")
st.title("🧭 PNL aero generator")

# Meni
opcija = st.sidebar.radio("Odaberi vrstu obrade", ["✈️ Obrada za Aero", "🛫 Obrada za Avio"])

# --------------------------------------------------
# ✈️ AERO OBRADA (.txt za aerodrom)
# --------------------------------------------------
if opcija == "✈️ Obrada za Aero":
    st.header("✈️ Aero PNL Generator")
    uploaded_file = st.file_uploader("📤 Učitaj .xlsx fajl", type="xlsx")

    def validate_passenger(row):
        warnings = []
        if not str(row.get('Passenger Surname', '')).strip():
            warnings.append("Nedostaje prezime")
        if not str(row.get('Passenger Name', '')).strip():
            warnings.append("Nedostaje ime")
        if str(row.get('Title', '')).strip().upper() not in ["MR", "MRS", "CHD", "INF"]:
            warnings.append("Nepoznata ili nedostajuća titula")

        passport = str(row.get('Passport', '')).strip().upper()
        if not passport or passport in ['NAN', '']:
            warnings.append("Nedostaje broj pasoša")
        elif not re.match(r'^[A-Z0-9]{5,10}$', passport):
            warnings.append("Pasoš neispravan")

        birthday = pd.to_datetime(row.get('Birthday', None), errors='coerce')
        if pd.isna(birthday):
            warnings.append("Datum rođenja neispravan ili nedostaje")

        expiry = pd.to_datetime(row.get('Pass Expire Date', None), errors='coerce')
        if pd.isna(expiry):
            warnings.append("Datum isteka pasoša neispravan ili nedostaje")

        nationality = str(row.get('Nationality', '')).strip()
        if not nationality or nationality.lower() in ['nan', '']:
            warnings.append("Nedostaje nacionalnost")

        return warnings

    def format_passenger(row):
        warnings = validate_passenger(row)
        surname = str(row.get('Passenger Surname', '')).strip().upper()
        name = str(row.get('Passenger Name', '')).strip().upper()
        title = str(row.get('Title', '')).strip().upper()
        full_name = f"{surname}/{name}"

        passport_number = str(row.get('Passport', '')).strip().upper()
        if not passport_number or passport_number in ['NAN', '']:
            passport_number = "XXXXXXX"

        nationality_raw = str(row.get('Nationality', '')).strip()
        nationality = "BIH" if "Bosnia" in nationality_raw else nationality_raw.upper()
        if not nationality or nationality in ['NAN', '']:
            nationality = "XXX"

        passport_expiry = pd.to_datetime(row.get('Pass Expire Date', None), errors='coerce')
        passport_expiry_str = passport_expiry.strftime('%d%b%y').upper() if pd.notna(passport_expiry) else "XXMMMXX"

        birthday = pd.to_datetime(row.get('Birthday', None), errors='coerce')
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
        try:
            # Prvi pokušaj
            df = pd.read_excel(uploaded_file, header=3)
            expected = ['Passenger Surname', 'Passenger Name', 'Title', 'Passport', 'Nationality', 'Pass Expire Date', 'Birthday']
            if not all(col in df.columns for col in expected):
                raise ValueError("Kolone nisu prepoznate")
            st.success("✅ Uspješno učitan fajl (standardna struktura)!")
        except Exception as e:
            st.warning(f"⚠️ Neuspjeh u standardnoj obradi: {e}. Pokušavam rezervni format...")
            try:
                df = pd.read_excel(uploaded_file, header=None, skiprows=3, usecols="A:H")
                df.columns = ['Reservation', 'Passenger Surname', 'Passenger Name', 'Title',
                              'Nationality', 'Passport', 'Birthday', 'Pass Expire Date']
                st.success("✅ Uspješno učitan fajl (rezervna logika)!")
            except Exception as e2:
                st.error(f"❌ Neuspjeh u rezervnom načinu: {e2}")
                st.stop()

        df["Upozorenja"] = df.apply(lambda r: ", ".join(validate_passenger(r)), axis=1)
        st.subheader("📋 Učitani podaci")
        st.dataframe(df)

        if df["Upozorenja"].str.len().max() > 0:
            st.warning("⚠️ Neki putnici imaju upozorenja. Provjeri ih prije slanja.")

        txt_output = "\n\n".join(df.apply(format_passenger, axis=1))
        st.subheader("📑 Generisani .txt sadržaj")
        st.text_area("Pregled sadržaja", txt_output, height=500)

        st.download_button(
            label="📥 Preuzmi .txt fajl",
            data=txt_output,
            file_name="aerodrom_export.txt",
            mime="text/plain"
        )
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
            res_raw = row["Reservation"] if pd.notna(row["Reservation"]) else "FALI REZERVACIJA"
            if res_raw not in res_map:
                res_map[res_raw] = f"10000{res_counter}"
                res_counter += 1
            res_code = res_map[res_raw]

            title = str(row["Title"]).strip().upper() if pd.notna(row["Title"]) else "FALI TITULA"
            surname = str(row["Surname"]).strip().upper()
            name = str(row["Name"]).strip().upper()

            if title == "MR":
                suffix = "MR"
            elif title == "MRS":
                suffix = "MRS"
            elif title == "CHD":
                suffix = "CHD"
            elif title == "INF":
                suffix = "INF"
            else:
                suffix = title

            line = f"1{surname}/{name}{suffix} .L/{res_code}"
            if suffix == "INF":
                line = f" .R/INFT  {line}"
            elif suffix == "CHD":
                line = f" .R/1CHD  {line}"

            output_lines.append(line)

        output_lines.append("ENDPNL")
        final_txt = "\n".join(output_lines)

        st.subheader("📄 Generisani .txt sadržaj")
        st.code(final_txt, language="text")

        def get_download_link(text):
            b64 = base64.b64encode(text.encode()).decode()
            date = datetime.datetime.now().strftime("%d%m%Y")
            file_name = f"PNL_Export_{date}.txt"
            href = f'<a href="data:file/txt;base64,{b64}" download="{file_name}">📥 Preuzmi .txt fajl</a>'
            return href

        st.markdown(get_download_link(final_txt), unsafe_allow_html=True)
    else:
        st.info("Učitaj .xlsx fajl da započneš obradu.")
