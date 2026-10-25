import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="分解ESR解析", layout="wide")
st.title("コンデンサ内部構造とESRの解析")
st.caption("ExcelのSheet1のみを読み込みます。Sheet2は使用しません。")

# ExcelのSheet1に実際にある列名を使用する
REQUIRED_COLUMNS = [
    "表示容量[μF]", "耐電圧[V]", "耐熱温度[℃]", "メーカー", "ESR[Ω]",
    "陽極面積[㎠]", "陰極面積[㎠]", "電極間距離[nm]", "封口部高さ[cm]", "構造"
]
NUMERIC_COLUMNS = [
    "表示容量[μF]", "耐電圧[V]", "耐熱温度[℃]", "ESR[Ω]",
    "陽極面積[㎠]", "陰極面積[㎠]", "電極間距離[nm]", "封口部高さ[cm]"
]
STRUCTURES = ["A", "B", "C", "D"]

uploaded_file = st.file_uploader("分解ESR.xlsx を選択", type=["xlsx", "xlsm"])
if uploaded_file is None:
    st.info("まず、測定データのExcelファイルをアップロードしてください。Sheet1だけを読み込みます。")
    st.stop()

try:
    # 先頭のワークシート（Sheet1）のみを読み込む
    df = pd.read_excel(uploaded_file, sheet_name=0)
except Exception as e:
    st.error(f"Excelファイルを読み込めませんでした：{e}")
    st.stop()

missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
if missing:
    st.error("必要な列が見つかりません。Excelの列名を確認してください：" + "、".join(missing))
    st.write("読み込まれた列名", list(df.columns))
    st.stop()

# 数値列を数値型に変換。空欄や数値にできない値は欠損値にする。
for col in NUMERIC_COLUMNS:
    df[col] = pd.to_numeric(df[col], errors="coerce")
for col in ["メーカー", "構造"]:
    df[col] = df[col].astype("string").str.strip()

st.sidebar.header("データの絞り込み")

def multi_filter(label, col):
    values = sorted(df[col].dropna().unique().tolist(), key=lambda x: str(x))
    return st.sidebar.multiselect(label, options=values, default=values)

voltage_values = multi_filter("耐電圧[V]", "耐電圧[V]")
temp_values = multi_filter("耐熱温度[℃]", "耐熱温度[℃]")
manufacturer_values = multi_filter("メーカー", "メーカー")

filtered = df[
    df["耐電圧[V]"].isin(voltage_values)
    & df["耐熱温度[℃]"].isin(temp_values)
    & df["メーカー"].isin(manufacturer_values)
].copy()

st.caption(f"表示対象：{len(filtered)} / 全{len(df)}件")
if filtered.empty:
    st.warning("選択した条件に該当するデータがありません。絞り込み条件を変更してください。")
    st.stop()

# ------------------------------------------------------------
# 1. ESRと選択した内部構造パラメータの散布図
# ------------------------------------------------------------
st.subheader("1. ESRとの散布図")
y_choice = st.selectbox(
    "縦軸に表示する項目",
    ["陽極面積", "陰極面積", "陽極面積＋陰極面積", "電極間距離", "封口部高さ"],
    index=0,
)
hover_cols = ["メーカー", "耐電圧[V]", "耐熱温度[℃]", "構造", "表示容量[μF]"]

if y_choice == "陽極面積":
    y_col = "陽極面積[㎠]"
    plot_df = filtered.dropna(subset=["ESR[Ω]", y_col])
    fig = px.scatter(plot_df, x="ESR[Ω]", y=y_col, hover_data=hover_cols)
    fig.update_yaxes(title="陽極面積 [cm²]")
elif y_choice == "陰極面積":
    y_col = "陰極面積[㎠]"
    plot_df = filtered.dropna(subset=["ESR[Ω]", y_col])
    fig = px.scatter(plot_df, x="ESR[Ω]", y=y_col, hover_data=hover_cols)
    fig.update_yaxes(title="陰極面積 [cm²]")
elif y_choice == "陽極面積and陰極面積":
    plot_df = filtered.dropna(subset=["ESR[Ω]", "陽極面積[㎠]", "陰極面積[㎠]"])
    long_df = plot_df.melt(
        id_vars=hover_cols + ["ESR[Ω]"],
        value_vars=["陽極面積[㎠]", "陰極面積[㎠]"],
        var_name="電極", value_name="面積[cm²]",
    )
    fig = px.scatter(
        long_df, x="ESR[Ω]", y="面積[cm²]", color="電極",
        hover_data=hover_cols,
    )
    fig.update_yaxes(title="電極面積 [cm²]")
elif y_choice == "電極間距離":
    y_col = "電極間距離[nm]"
    plot_df = filtered.dropna(subset=["ESR[Ω]", y_col])
    fig = px.scatter(plot_df, x="ESR[Ω]", y=y_col, hover_data=hover_cols)
    fig.update_yaxes(title="電極間距離 [nm]")
else:
    y_col = "封口部高さ[cm]"
    plot_df = filtered.dropna(subset=["ESR[Ω]", y_col])
    fig = px.scatter(plot_df, x="ESR[Ω]", y=y_col, hover_data=hover_cols)
    fig.update_yaxes(title="封口部高さ [cm]")

if plot_df.empty:
    st.warning("この項目を描画できる有効なデータがありません。")
else:
    fig.update_layout(xaxis_title="ESR [Ω]", height=560, legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"この散布図に使用したデータ：{len(plot_df)}件")

# ------------------------------------------------------------
# 2. 全容量の構造別ESR箱ひげ図
# ------------------------------------------------------------
st.divider()
st.subheader("2. 全容量の構造別ESRの箱ひげ図")
st.write("容量を分けず、フィルター後の全データで構造A・B・C・DのESR分布を比較します。")

box_df = filtered.dropna(subset=["表示容量[μF]", "構造", "ESR[Ω]"]).copy()
box_df = box_df[box_df["構造"].isin(STRUCTURES)].copy()

if box_df.empty:
    st.warning("箱ひげ図に使えるデータがありません。")
else:
    fig_all = px.box(
        box_df,
        x="構造",
        y="ESR[Ω]",
        category_orders={"構造": STRUCTURES},
        points="all",
        hover_data=["メーカー", "耐電圧[V]", "耐熱温度[℃]", "表示容量[μF]"],
    )
    fig_all.update_layout(
        title="全容量の構造別ESR分布",
        xaxis_title="構造",
        yaxis_title="ESR [Ω]",
        height=500,
    )
    st.plotly_chart(fig_all, use_container_width=True)

    all_counts = (
        box_df["構造"].value_counts()
        .reindex(STRUCTURES, fill_value=0)
        .rename("測定データ数")
        .rename_axis("構造")
    )
    st.write("全容量：構造ごとの測定データ数")
    st.dataframe(all_counts.to_frame(), use_container_width=True)
    st.caption(f"全容量の測定データ数：{len(box_df)}件")

# ------------------------------------------------------------
# 3. 容量帯別・構造別ESRの箱ひげ図（2容量帯×A～D）
# ------------------------------------------------------------
st.divider()
st.subheader("3. 容量帯別・構造別ESRの箱ひげ図")
st.write("容量帯ごとに、構造A・B・C・DのESR分布を比較します。フィルター条件は散布図・全容量グラフと共通です。")

capacity_bands = [
    ("1～47 μF", 1, 47),
    ("100～1000 μF", 100, 1000),
]

for band_name, lower, upper in capacity_bands:
    band_df = box_df[box_df["表示容量[μF]"].between(lower, upper, inclusive="both")].copy()
    st.markdown(f"### 容量帯：{band_name}")

    if band_df.empty:
        st.warning(f"{band_name}に該当するデータがありません。")
        continue

    fig_box = px.box(
        band_df,
        x="構造",
        y="ESR[Ω]",
        category_orders={"構造": STRUCTURES},
        points="all",
        hover_data=["メーカー", "耐電圧[V]", "耐熱温度[℃]", "表示容量[μF]"],
    )
    fig_box.update_layout(
        title=f"{band_name}の構造別ESR分布",
        xaxis_title="構造",
        yaxis_title="ESR [Ω]",
        height=500,
    )
    st.plotly_chart(fig_box, use_container_width=True)

    counts = (
        band_df["構造"].value_counts()
        .reindex(STRUCTURES, fill_value=0)
        .rename("測定データ数")
        .rename_axis("構造")
    )
    st.write(f"{band_name}：構造ごとの測定データ数")
    st.dataframe(counts.to_frame(), use_container_width=True)
    st.caption(f"この容量帯の測定データ数：{len(band_df)}件")

st.caption(
    "箱は第1四分位数～第3四分位数、中央線は中央値を示します。"
    "点は個々の測定データです。容量帯の分類には表示容量を使用しています。"
    "47 μF超～100 μF未満、および1000 μF超のデータは容量帯別グラフには含まれませんが、全容量グラフには含まれます。"
)

with st.expander("現在の絞り込み後データを確認"):
    st.dataframe(filtered, use_container_width=True)
