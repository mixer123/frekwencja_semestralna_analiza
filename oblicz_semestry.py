import pandas as pd
import re
import json

lata = ['2020_2021','2021_2022','2022_2023','2023_2024','2024_2025','2025_2026']

GRANICE = {
    '2020_2021': {'koniec_sem1': '2020-12-22', 'poczatek_sem2': '2021-01-18'},
    '2021_2022': {'koniec_sem1': '2022-01-28', 'poczatek_sem2': '2022-02-14'},
    '2022_2023': {'koniec_sem1': '2023-02-10', 'poczatek_sem2': '2023-02-27'},
    '2023_2024': {'koniec_sem1': '2024-01-12', 'poczatek_sem2': '2024-01-29'},
    '2024_2025': {'koniec_sem1': '2024-12-20', 'poczatek_sem2': '2025-01-07'},
    '2025_2026': {'koniec_sem1': '2025-12-19', 'poczatek_sem2': '2026-01-07'},
}

kolumny_nieobecnosci = ['nieob. uspr. p.s.', 'nieob. uspraw.', 'nieobecność']
kolumny_obecnosci = ['nauka zdalna', 'obecność', 'spóźn. uspr.', 'spóźnienie', 'zwolniony']
wszystkie_wpisy = kolumny_nieobecnosci + kolumny_obecnosci

def numer_klasy(dziennik):
    m = re.match(r"^(\d+)", str(dziennik))
    return int(m.group(1)) if m else None

def dziennik_na_rocznik(dziennik, rok_szkolny):
    rok_start = int(rok_szkolny.split("/")[0])
    nr = numer_klasy(dziennik)
    if nr:
        return rok_start - nr + 1
    return None

frames = []
for rok in lata:
    df = pd.read_csv(f'wyniki_semestralne/agg_{rok}.csv')
    df['Data'] = pd.to_datetime(df['Data'])
    df = df[df['Wpis'].isin(wszystkie_wpisy)].copy()
    rok_szkolny = rok.replace('_', '/')
    # zgodnie z analiza_v2_DASHBOARD_FINALNY.ipynb (komorka 5): odciecie 1 wrzesnia (wylacznie)
    rok_start_num = rok_szkolny.split('/')[0]
    odciecie_wrzesien = pd.Timestamp(f'{rok_start_num}-09-01')
    df = df[df['Data'] > odciecie_wrzesien].copy()
    g = GRANICE[rok]
    koniec_sem1 = pd.Timestamp(g['koniec_sem1'])
    poczatek_sem2 = pd.Timestamp(g['poczatek_sem2'])
    rok_koniec = rok_szkolny.split('/')[1]
    koniec_kwietnia = pd.Timestamp(f"{rok_koniec}-04-30")

    df['numer_klasy'] = df['Dziennik'].apply(numer_klasy)
    df['semestr'] = None
    df.loc[df['Data'] <= koniec_sem1, 'semestr'] = 'I'
    df.loc[df['Data'] >= poczatek_sem2, 'semestr'] = 'II'
    df = df.dropna(subset=['semestr']).copy()

    maska_odciecia = (df['numer_klasy'] == 5) & (df['semestr'] == 'II') & (df['Data'] > koniec_kwietnia)
    df = df[~maska_odciecia].copy()

    df['rok_szkolny'] = rok_szkolny
    frames.append(df)

df_all = pd.concat(frames, ignore_index=True)

wynik = (
    df_all
    .groupby(['rok_szkolny', 'semestr', 'Dziennik'])
    .apply(lambda x: pd.Series({
        'wszystkich': x[x['Wpis'].isin(wszystkie_wpisy)]['Liczba'].sum(),
        'nieobecnych': x[x['Wpis'].isin(kolumny_nieobecnosci)]['Liczba'].sum(),
    }), include_groups=False)
    .reset_index()
)
wynik['frekwencja_pct'] = ((wynik['wszystkich'] - wynik['nieobecnych']) / wynik['wszystkich'] * 100).round(1)
wynik['rocznik'] = wynik.apply(lambda r: dziennik_na_rocznik(r['Dziennik'], r['rok_szkolny']), axis=1)
wynik['numer_klasy'] = wynik['Dziennik'].apply(numer_klasy)
wynik['sufiks'] = wynik['Dziennik'].str.extract(r"^\d+(.*)")

lata_sort = {rok.replace('_','/'): i for i, rok in enumerate(lata)}
wynik['sort_rok'] = wynik['rok_szkolny'].map(lata_sort)
wynik['sort_sem'] = wynik['semestr'].map({'I': 0, 'II': 1})
wynik = wynik.sort_values(['Dziennik', 'sort_rok', 'sort_sem']).reset_index(drop=True)

wynik.to_csv('wyniki_semestralne/frekwencja_semestralna_pelna.csv', index=False, encoding='utf-8')
print(wynik.shape)
print(wynik.head(20).to_string())
print()
print("Liczba unikalnych klas (Dziennik):", wynik['Dziennik'].nunique())
print("Zakres lat:", sorted(wynik['rok_szkolny'].unique()))
print("Braki (NaN) w frekwencja_pct:", wynik['frekwencja_pct'].isna().sum())
