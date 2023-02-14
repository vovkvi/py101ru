#!/usr/bin/env python3
# coding: utf-8
'''
Простой скрипт для парсинга интернет радиостанций сайта 101.ru, который
позволяет создать файл плейлиста (*.m3u) для выбранного музыкального
жанра.

(с) Vitalii Vovk, 2022
'''
import os
import json
import ssl
import urllib.request

from bs4 import BeautifulSoup


CHANNEL_SERVERS_URL = 'https://101.ru/api/channel/getListServersChannel'
GROUPS_URL = 'https://101.ru/radio-top'


def get_page(url:str, data_enable:bool=True, timeout:int=10) -> tuple:
    '''
    Получает код ответа и данные по указанному url

    :params:
        url         (str)  : ссылка на страницу
        data_enable (bool) : если задано True, то функция возвращает
                             содержимое страницы и код ответа, если же
                             задано False - вернет только код ответа,
                             а вместо содержимого запишет None.
    :return:
        tuple(код ответа, содержимое страницы)
    '''
    code = 404
    data = None
    try:
        with urllib.request.urlopen(url, timeout=timeout, context=ssl.create_default_context()) as conn:
            code = conn.getcode()
            data = conn.read().decode() if data_enable else None
    except urllib.error.HTTPError as e:
        code = e.code
        data = f'[-] HTTP Error: {e.reason}'
    except urllib.error.URLError as e:
        data = f'[-] URL Error: {e.reason}'
    except ValueError as e:
        data = f'[-] Value Error: {e}'
    return code, data


def get_channel_genres_list() -> list:
    '''
    Ищет и составляет список жанров каналов

    :return:
        list(
            dict(
                'title' : str,
                'url'   : str
            )
        )
    '''
    result = []
    code, data = get_page(GROUPS_URL)
    if code != 200:
        print(data)
        return
    soup = BeautifulSoup(data, 'html.parser')
    groups = soup.select('ul.channel-groups li a[href]')
    if not groups:
        print(f'[-] ERROR: Не удалось составить список групп каналов.')
        return
    for gr in groups:
        tag = gr.get('href')
        if not tag or tag == '#':
            continue
        result.append({
            'title' : gr.text.strip(),
            'url'   : f"https://101.ru{tag}"
        })
    return result


def get_stations_url(genre_url:str) -> set:
    '''
    Получает список URL всех станций указанного жанра.

    :params:
        genre_url (str) : ссылка на страницу жанра

    :return:
        set(str)
    '''
    code, data = get_page(genre_url)
    if code != 200:
        print(data)
        return
    soup = BeautifulSoup(data, 'html.parser')
    divs = soup.select('div.grid li a[href]')
    if not divs:
        print('[-] ERROR: Не удалось составить список групп каналов.')
        return
    return set([f"https://101.ru{x.get('href')}" for x in divs])


def get_channel_info(url:str) -> dict:
    '''
    Получает информацию о конкретном радиоканале.

    :params:
        url (str) : ссылка на страницу радиоканала
    :return:
        json из API 101.ru
    '''
    number = url.split('/')[-1]
    code, data = get_page(f'{CHANNEL_SERVERS_URL}/{number}/channel/')
    return json.loads(data) if code == 200 else data


def get_channel_streams(url: str) -> list:
    '''
    Получает список ссылок на потоки вещания канала.

    :params:
        url (str) : ссылка на страницу канала

    :return:
        list(
            dict(
                'title'  : str,
                'stream' : str
            )
        )
    '''
    result = []
    chnls = get_stations_url(url)
    for ch in chnls:
        ch_num = ch.split('/')[-1]
        info = get_channel_info(ch_num)
        if info.get('status') is not None and info.get('status') == 1:
            result.append({
                'title' : info['result'][0]['titleChannel'],
                'stream' : [x['urlStream'].split('?')[0] for x in info['result']]
                })
    return result


def make_m3u(name:str, channels:dict):
    '''
    Создает файл плейлиста (*.m3u) со списком рабочих каналов
    выбранного жанра

    :params:
        name     (str) : Имя плейлиста
        channels (str) : список каналов
    '''
    m3u = open(f'{name}.m3u', 'w+', encoding='utf-8', errors='ignore')
    m3u.write('#EXTM3U\n')
    i = 0
    for val in channels:
        active_stream = None
        for s in val['stream']:
            code = 404
            if s.startswith('http'):
                code, data = get_page(s, False)
            if code == 200:
                active_stream = s
                break
        if not active_stream:
            print(f'[-] ERROR: {val["title"]}')
            continue
        m3u.write(f'#EXTINF: {i}, {val["title"]}\n{active_stream}\n')
        i += 1
    m3u.close()


def main():
    genres = get_channel_genres_list()
    if not genres:
        return
    for idx, g in enumerate(genres):
        print(f"[{idx:>3} ] {g['title']}")

    num = input('Выберите жанр: ')
    itm = genres[int(num)]

    print(f"\n[i] Идет создание m3u для жанра <{itm['title']}>...")
    make_m3u(itm['title'], get_channel_streams(itm['url']))


if __name__ == '__main__':
    main()
    print(f'\nВыполнение завершено.')
