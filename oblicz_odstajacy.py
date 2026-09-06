import pandas as pd
import re

lata = ['2020_2021','2021_2022','2022_2023','2023_2024','2024_2025','2025_2026']

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
    df = pd.read_csv(f'wyniki_semestralne/agg_uczniowie_{rok}.csv')
    df['rok_szkolny'] = rok.replace('_', '/')
    frames.append(df)

df = pd.concat(frames, ignore_index=True)
df['frekwencja_pct'] = ((df['wszystkich'] - df['nieobecnych']) / df['wszystkich'] * 100).round(1)
df['rocznik'] = df.apply(lambda r: dziennik_na_rocznik(r['Dziennik'], r['rok_szkolny']), axis=1)
df['sufiks'] = df['Dziennik'].str.extract(r"^\d+(.*)")

# IQR per (rok_szkolny, semestr, Dziennik) - tak jak w analiza_v2_DASHBOARD_FINALNY.ipynb (cell 18-19),
# rozszerzone o wymiar semestru
Q1 = df.groupby(['rok_szkolny','semestr','Dziennik'])['frekwencja_pct'].transform('quantile', 0.25)
Q3 = df.groupby(['rok_szkolny','semestr','Dziennik'])['frekwencja_pct'].transform('quantile', 0.75)
IQR = Q3 - Q1
df['dolna_granica'] = (Q1 - 1.5 * IQR).round(2)
df['odstajacy'] = df['frekwencja_pct'] < df['dolna_granica']

df.to_csv('wyniki_semestralne/uczniowie_semestralne_pelne.csv', index=False, encoding='utf-8')

# podsumowanie per rok_szkolny + semestr + Dziennik
podsumowanie = (
    df.groupby(['rok_szkolny','semestr','Dziennik'])
    .apply(lambda g: pd.Series({
        'liczba_uczniow': len(g),
        'liczba_odstajacych': g['odstajacy'].sum(),
        'frekwencja_z_odstajacymi': round(g['frekwencja_pct'].mean(), 1),
        'frekwencja_bez_odstajacych': round(g.loc[~g['odstajacy'], 'frekwencja_pct'].mean(), 1) if (~g['odstajacy']).any() else None,
    }), include_groups=False)
    .reset_index()
)
podsumowanie['pct_odstajacych'] = (podsumowanie['liczba_odstajacych'] / podsumowanie['liczba_uczniow'] * 100).round(1)
podsumowanie.to_csv('wyniki_semestralne/odstajacy_podsumowanie.csv', index=False, encoding='utf-8')

print("liczba wierszy uczen-klasa-semestr:", len(df))
print("liczba odstajacych (wszystkie okresy):", df['odstajacy'].sum(), "/", len(df), f"({df['odstajacy'].mean()*100:.1f}%)")
print()
print(podsumowanie.sort_values('pct_odstajacych', ascending=False).head(15).to_string())
print()
trend = df.groupby(['rok_szkolny','semestr']).agg(
    liczba_uczniow=('odstajacy','size'),
    liczba_odstajacych=('odstajacy','sum'),
).reset_index()
trend['pct'] = (trend['liczba_odstajacych']/trend['liczba_uczniow']*100).round(1)
print(trend.to_string())
