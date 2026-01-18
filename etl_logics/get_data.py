import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import urllib3
from io import StringIO
from tqdm import tqdm

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

cookies = {
    '_csrf-frontend': 'b9a25c2ba852b42be56860ccbfaec89e31deb4e09fa33d7be0901b413f7ed8ada%3A2%3A%7Bi%3A0%3Bs%3A14%3A%22_csrf-frontend%22%3Bi%3A1%3Bs%3A32%3A%22kocAv8bQa_2P6oiSo1uC80fDpwpc2F6z%22%3B%7D',
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://narx.idm.uz/',
}

base_params = {
    'id': '452',
    'filter[64][filter_id]': '64',
    'filter[64][attribute_id]': 'all_dist',
}

def get_all_dates():
    """Получает список всех доступных дат с сайта"""
    print("🔄 Получаем список всех доступных дат...")
    try:
        init_params = base_params.copy()
        init_params['period_id'] = '1186' 
        
        r = requests.get('https://narx.idm.uz/view/post/index452', 
                         params=init_params, cookies=cookies, headers=headers, verify=False)
        
        soup = BeautifulSoup(r.text, 'html.parser')
        select = soup.find('select', {'name': 'period_id'})
        
        dates_dict = {}
        if select:
            options = select.find_all('option')
            for opt in options:
                val = opt.get('value')
                text = opt.text.strip()
                if val:
                    dates_dict[val] = text
            print(f"✅ Найдено периодов: {len(dates_dict)}")
            return dates_dict
        else:
            print("❌ Не удалось найти список дат. Проверьте Cookie.")
            return {}
            
    except Exception as e:
        print(f"Ошибка при поиске дат: {e}")
        return {}

def process_single_date(p_id, description):
    current_params = base_params.copy()
    current_params['period_id'] = p_id
    
    try:
        r = requests.get('https://narx.idm.uz/view/post/index452', 
                         params=current_params, cookies=cookies, headers=headers, verify=False)
        
        dfs = pd.read_html(StringIO(r.text), match='Pomidor', decimal='.', thousands=' ')
        df = dfs[0]

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [' '.join(map(str, col)).strip() for col in df.columns.values]

        product_col = next((c for c in df.columns if 'Маҳсулотлар' in c or 'Mahsulotlar' in c), None)
        
        if not product_col:
            return None

        df = df.set_index(product_col)
        cols_to_drop = [c for c in df.columns if '№' in c or 'Ўртача' in c or 'Average' in c]
        df = df.drop(columns=cols_to_drop, errors='ignore')
        df_transposed = df.T
        
        df_transposed.index.name = 'Region'
        df_transposed.reset_index(inplace=True)
        df_transposed['Region'] = df_transposed['Region'].str.replace('Туманлар ', '', regex=False)
        
        df_transposed.insert(0, 'Date_ID', p_id)
        df_transposed.insert(1, 'Description', description)
        
        return df_transposed

    except ValueError:
        return None
    except Exception as e:
        print(f"  Ошибка на дате {p_id}: {e}")
        return None

def main():
    all_dates = get_all_dates()
    
    if not all_dates:
        return

    all_dates = {'3910': all_dates.get('3910', 'Неизвестная дата')} # Kerakli sana IDsi qo'yiladi
    big_data_list = []
    
    print("🚀 Начинаю сбор данных...")
    
    loop = tqdm(all_dates.items(), desc="Скачивание", unit="дата")

    for p_id, p_desc in loop:        
        df_day = process_single_date(p_id, p_desc)
        
        if df_day is not None:
            big_data_list.append(df_day)
        else:
            tqdm.write(f"⚠️ ID {p_id}: Нет данных")
        
        time.sleep(0.5)

    if big_data_list:
        print("\n📥 Объединение всех данных...")
        final_df = pd.concat(big_data_list, ignore_index=True)
        
        filename = "product_prices_01_14.xlsx"
        final_df.to_excel(filename, index=False)
        
        print(f"Файл сохранен: {filename}")
        print(f"Всего строк: {len(final_df)}")
        print(f"Всего колонок: {len(final_df.columns)}")
    else:
        print("❌ Данные не были собраны.")

if __name__ == "__main__":
    main()