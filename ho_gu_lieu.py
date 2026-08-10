import fitz  # PyMuPDF
import pdfplumber
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import re

# === Danh sách tên ngành dễ đọc ===
list_nganh = {
    '7480201KMA': 'Công nghệ thông tin KMA',
    '7480202KMA': 'An toàn thông tin KMA',
    '7520207': 'Kỹ thuật ĐTVT KMA',
    '7480201KMP': 'Công nghệ thông tin KMP',
    '7480202KMP': 'An toàn thông tin KMP'
}

# === Xử lý file 2022, 2024 bằng fitz ===
def chuyen_df(path):
    dfs = []
    doc = fitz.open(path)
    pdf_name = os.path.basename(path)
    match_year = re.search(r'20\d{2}', pdf_name)
    year = match_year.group(0) if match_year else "unknown"

    for page in doc:
        tables = page.find_tables()
        for table in tables.tables:
            df = pd.DataFrame(table.extract())
            for i, row in df.iterrows():
                if 'Mã ngành' in row.values.tolist():
                    df.columns = row
                    df = df[i+1:]
                    break
            else:
                continue
            if 'Mã ngành' in df.columns:
                dfs.append(df)

    if not dfs:
        print(f"❌ Không có bảng hợp lệ: {path}")
        return pd.DataFrame()

    df_all = pd.concat(dfs, ignore_index=True).replace('', pd.NA)

    # Tìm cột điểm
    diem_col = None
    for col in df_all.columns:
        if "điểm" in str(col).lower() and ("trúng" in str(col).lower() or "tt" in str(col).lower()):
            diem_col = col
            break

    if diem_col is None or 'Mã ngành' not in df_all.columns:
        print(f"❌ File lỗi thiếu 'Mã ngành' hoặc 'Điểm trúng tuyển': {path}")
        print(f"📌 Các cột hiện có: {df_all.columns.tolist()}")
        return pd.DataFrame()

    df_all = df_all.dropna(subset=['Mã ngành', diem_col])
    df_all.rename(columns={diem_col: 'Điểm trúng tuyển'}, inplace=True)
    df_all['Năm'] = year
    df_all = df_all.replace({'N7480201KMP': '7480201KMP'})

    print(f"✅ Đã đọc {path} - Số dòng: {len(df_all)} | Mã ngành: {df_all['Mã ngành'].unique().tolist()}")
    return df_all

# === Xử lý file 2023 bằng pdfplumber (sửa regex) ===
def chuyen_df_pdfplumber(path):
    year_match = re.search(r'20\d{2}', path)
    year = year_match.group(0) if year_match else 'unknown'
    data = []

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split('\n')
            for line in lines:
                match = re.match(
                    r'^(\d+)\s+(\d{8})\s+(\d+)\s+(.+?)\s+(\d{7}[A-Z]*)\s+([A-Z0-9]+)\s+(\d+)\s+([\d\.]+)\s+30$',
                    line
                )
                if match:
                    stt, sbd, cmnd, hoten, manganh, tohop, thutunv, diem = match.groups()
                    data.append({
                        'STT': stt,
                        'SBD': sbd,
                        'CMND': cmnd,
                        'Họ Tên': hoten,
                        'Mã ngành': manganh,
                        'Mã tổ hợp': tohop,
                        'Thứ tự NV': thutunv,
                        'Điểm trúng tuyển': diem,
                        'Năm': year
                    })

    df = pd.DataFrame(data)
    if not df.empty:
        print(f"✅ [PLUMBER] {path} - {len(df)} dòng | Mã ngành: {df['Mã ngành'].unique().tolist()}")
    else:
        print(f"❌ Không trích được dữ liệu từ: {path}")
    return df

# === Tính trung bình điểm trúng tuyển ===
def tinh_trung_binh(df_all):
    df_all = df_all[pd.to_numeric(df_all['Điểm trúng tuyển'], errors='coerce').notnull()]
    df_all['Điểm trúng tuyển'] = df_all['Điểm trúng tuyển'].astype(float)
    df_all = df_all[df_all['Điểm trúng tuyển'] > 10]  # Loại điểm sai
    return df_all.groupby(['Mã ngành', 'Năm'])['Điểm trúng tuyển'].mean().reset_index()

# === Vẽ biểu đồ giữ ngành thiếu năm ===
def ve_bieu_do(df_avg, output_path):
    df_avg['Tên ngành'] = df_avg['Mã ngành'].apply(lambda x: list_nganh.get(x, x))
    df_pivot = df_avg.pivot(index='Tên ngành', columns='Năm', values='Điểm trúng tuyển')
    df_pivot = df_pivot[list(sorted(df_pivot.columns))]

    ax = df_pivot.plot(kind='bar', figsize=(14, 6), edgecolor='black')
    plt.title('Điểm trúng tuyển theo năm và ngành', fontsize=14)
    plt.xlabel('Tên Ngành')
    plt.ylabel('Điểm')
    plt.xticks(rotation=0)
    plt.legend(title='Năm')
    plt.tight_layout()

    for container in ax.containers:
        for bar in container:
            height = bar.get_height()
            if not np.isnan(height):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    height + 0.1,
                    f"{height:.2f}",
                    ha='center',
                    va='bottom',
                    fontsize=10
                )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, format='png')
    plt.close()
    print(f"📊 Đã lưu biểu đồ tại: {output_path}")

# === MAIN ===
path_folder = '/home/ubuntu/Do_thi_KQ_TS'
list_file = os.listdir(path_folder)
list_df = []

for file in list_file:
    if file.endswith('.pdf') and any(year in file for year in ['2022', '2023', '2024']):
        full_path = os.path.join(path_folder, file)
        if '2023' in file:
            df = chuyen_df_pdfplumber(full_path)
        else:
            df = chuyen_df(full_path)
        if not df.empty:
            list_df.append(df)

if list_df:
    df_all = pd.concat(list_df, ignore_index=True)
    df_avg = tinh_trung_binh(df_all)
    output_path = '/home/ubuntu/HOCTAP/Do_thi_KQ_TS/do_thi_trung_binh_all_nam_theo_nganh.png'
    ve_bieu_do(df_avg, output_path)
else:
    print("❌ Không có dữ liệu hợp lệ.")
