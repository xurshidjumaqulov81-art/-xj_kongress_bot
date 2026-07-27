from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from pathlib import Path

async def make_excel(rows, path:str):
    wb=Workbook(); ws=wb.active; ws.title="Иштирокчилар"
    headers=["№","Telegram ID","Username","Исм-фамилия","XJ ID","Квалификация","Телефон","Вилоят","Жинс","Брон №","Пакет","USD","Сўм","Тўлов усули","Ҳолат","Сана"]
    ws.append(headers)
    for c in ws[1]: c.font=Font(bold=True); c.alignment=Alignment(horizontal='center')
    for i,r in enumerate(rows,1):
        ws.append([i,r['telegram_id'],r['username'],r['full_name'],r['xj_id'],r['qualification'],r['phone'],r['region'],r['gender'],r['booking_no'],r['package'],r['amount_usd'],r['amount_uzs'],r['payment_method'],r['status'],r['created_at']])
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width=min(max(len(str(x.value or '')) for x in col)+2,35)
    Path(path).parent.mkdir(parents=True,exist_ok=True); wb.save(path); return path

