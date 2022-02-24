from calendar import month
from os import mkdir
import requests
from typing import Dict, List, Tuple
from time import sleep
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import datetime  # Importei esse modulo para encontrar o ano atual
import shutil
from fpdf import FPDF

NOME_DO_CANDIDATO = 'Jonas Batista'
EMAIL_DO_CANDIDATO = 'jnsbatista2009@gmail.com'


MAIN_FOLDER = Path(__file__).parent.parent

today = datetime.date.today()
print(today)
this_year = int(today.strftime("%Y"))


def request_journals(start_date, end_date):
    url = 'https://engine.procedebahia.com.br/publish/api/diaries'

    r = requests.post(url, data={"cod_entity": '50', "start_date": start_date,
                                 "end_date": end_date})
    if r.status_code == 200:
        return r.json()
    elif r.status_code == 400:
        sleep(10)
        return request_journals(start_date, end_date)
    return {}


def download_jornal(edition, path):
    url = 'http://procedebahia.com.br/irece/publicacoes/Diario%20Oficial' \
          '%20-%20PREFEITURA%20MUNICIPAL%20DE%20IRECE%20-%20Ed%20{:04d}.pdf'.format(
              int(edition))
    r = requests.get(url, allow_redirects=True)
    if r.status_code == 200:
        with open(path, 'wb') as writer:
            writer.write(r.content)
        return edition, path
    return edition, ''


def download_mutiple_jornals(editions, paths):
    threads = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        for edition, path in zip(editions, paths):
            threads.append(executor.submit(download_jornal, edition, path))

        results = []
        for task in as_completed(threads):
            results.append(task.result())

    results = [[r for r in results if r[0] == e][0] for e in editions]
    return [r[1] for r in results]


class JournalDownloader:
    def __init__(self):
        self.pdfs_folder = MAIN_FOLDER / 'pdfs'
        self.jsons_folder = MAIN_FOLDER / 'out'

        self.pdfs_folder.mkdir(exist_ok=True)
        self.jsons_folder.mkdir(exist_ok=True)

        try:
            mkdir(r'.\pdfs')
        except:
            pass

    def get_day_journals(self, year: int, month: int, day: int) -> List[str]:
        # TODO: get all journals of a day, returns a list of JSON paths

        date = str(year if (1970 < year <= this_year) else this_year - 1) + "-"+str(month if (month > 9) else (
            "0"+str(month) if month != 0 else "01"))+"-"+str(day if (32 > day > 9) else ("0"+str(day) if day != 0 else "01"))

        return request_journals(date, date)

    def get_month_journals(self, year: int, month: int) -> List[str]:
        # TODO: get all journals of a month, returns a list of JSON paths
        date = str(year if (1970 < year <= this_year) else this_year - 1) + "-" + str(month if (month > 9) else (
            "0" + str(month) if month != 0 else "01")) + "-"
        d1 = "01"

        for d in range(31, 27, -1):
            if request_journals(date + d1, date + str(d)):
                return request_journals((date + d1), (date + str(d)))
            else:
                pass

    def get_year_journals(self, year: int) -> List[str]:
        # TODO: get all journals of a year, returns a list of JSON paths
        date = str(year if (1970 < year <= this_year) else this_year - 1)
        m0, m1, d0, d1 = "-01-", "-12-", "01", "31"

        return request_journals((date + m0 + d0), (date + m1 + d1))

    @staticmethod
    def parse(response: Dict) -> List[Tuple[str, str]]:
        # TODO: parses the response and returns a tuple list of the date and edition
        filter_dic = response['diaries']
        tuple_list = []
        for i in filter_dic:
            tuple_date = (i['data'], i['edicao'])
            tuple_list.append(tuple_date)

        return tuple_list

    def download_all(self, editions: List[str]) -> List[str]:
        # TODO: download journals and return a list of PDF paths. download in `self.pdfs_folder` folder
        #  OBS: make the file names ordered. Example: '0.pdf', '1.pdf', ...

        pdf = FPDF('P', 'mm', 'A4')

        pdf.add_page()

        pdf.set_font("Arial", size=8)

        edit_diaries = editions['diaries']
        data_i = str(edit_diaries[0]['data'])
        data_f = str(edit_diaries[-1]['data'])

        for dic in edit_diaries:
            for key, value in dic.items():
                st = (str(key) + ' : ' + str(value))
                ln = int(len(st)/100) if int(len(st)/100) > 0 else 1

                if ln > 1:
                    pdf.multi_cell(0, 5, str(st.encode(
                        'latin-1', 'replace').decode('latin-1')), 0,
                        'J', False)
                else:
                    pdf.cell(w=0, h=5.0, txt=st.encode(
                        'latin-1', 'replace').decode('latin-1'), border=0, ln=1)

        file_name = data_i + "_" + data_f + ".pdf"
        pdf.output(file_name)
        source = r'.\%s' % (file_name)
        destination = r'.\pdfs\%s' % (file_name)
        shutil.move(source, destination)

    def dump_json(self, pdf_path: str, edition: str, date: str) -> str:
        if pdf_path == '':
            return ''
        output_path = self.jsons_folder / f"{edition}.json"
        data = {
            'path': str(pdf_path),
            'name': str(edition),
            'date': date,
            'origin': 'Irece-BA/DOM'
        }
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(json.dumps(data,
                                  indent=4, ensure_ascii=False))
        return str(output_path)
