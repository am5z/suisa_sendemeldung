#!/usr/bin/env python3
from argparse import ArgumentParser
from csv import writer
from datetime import datetime, date, timedelta, timezone

import requests


class ACRClient:

    def __init__(self, access_key):
        self.access_key = access_key
        self.default_date = date.today()-timedelta(days=1)
        self.url = ('https://api.acrcloud.com/v1/'
                    'monitor-streams/{stream_id}/results')

    def get_data(self, stream_id, requested_date=None):
        if requested_date is None:
            requested_date = self.default_date
        url_params = dict(
            access_key=self.access_key,
            date=requested_date.strftime("%Y%m%d")
        )
        url = self.url.format(stream_id=stream_id)
        response = requests.get(url=url, params=url_params)
        response.raise_for_status()
        return response.json()


def write_csv(filename, data):
    header = [
        'Sendedatum',
        'Sendezeit',
        'Sendedauer',
        'Titel',
        'Künstler',
        'ISRC',
        'Label'
    ]
    with open(filename, mode='w') as csvfile:
        csvfile.write('sep=,\n')

        csv_writer = writer(csvfile, dialect='excel')
        csv_writer.writerow(header)

        for entry in data:
            metadata = entry.get('metadata')
            # parse timestamp (is in format "yyyy-mm-dd HH:MM:SS")
            timestamp = datetime.strptime(metadata.get('timestamp_utc'),
                                          '%Y-%m-%d %H:%M:%S')
            timestamp = (timestamp
                         .replace(tzinfo=timezone.utc)
                         .astimezone(tz=None))

            date = timestamp.strftime('%d/%m/%y')
            time = timestamp.strftime('%H:%M:%S')
            duration = timedelta(seconds=metadata.get('played_duration'))

            music = metadata.get('music')[0]
            title = music.get('title')
            artist = ', '.join([a.get('name') for a in music.get('artists')])
            if len(music.get('external_ids')) > 0:
                isrc = music.get('external_ids').get('isrc')
            else:
                isrc = ""
            label = music.get('label')
            score = music.get('score')

            csv_writer.writerow([date, time, duration, title,
                                 artist, isrc, label])
            if score < 50:
                print(metadata)
                print(score)
                quit(1)


if __name__ == '__main__':
    parser = ArgumentParser(
                description='ACRCloud client for SUISA reporting @ RaBe.')
    default_date = (date.today() - timedelta(days=1)).strftime("%Y%m%d")
    parser.add_argument('--access_key',
                        help='the access key for ACRCloud (required)',
                        required=True)
    parser.add_argument('--stream_id',
                        help='the id of the stream at ACRCloud (required)',
                        required=True)
    parser.add_argument('--date',
                        help='date in format YYYYMMDD to fetch data for \
                              (defaults to yesterday)',
                        default=default_date)
    parser.add_argument('--output',
                        help='file to write to (defaults to \
                             <script_name>_<date>.csv)')
    args = parser.parse_args()

    def print_error(msg):
        print('ERROR: {}\n'.format(msg))
        parser.print_help()
        quit(1)
    if not len(args.access_key) == 32:
        print_error('wrong format on access_key')

    client = ACRClient(args.access_key)
    data = []

    # calculate last day of last month
    last = date.today().replace(day=1) - timedelta(days=1)
    # calculate last day of month before
    current = last.replace(day=1) - timedelta(days=1)
    # iterate over the whole last month including last day of the month before
    while(current <= last):
        data = data + client.get_data(args.stream_id, requested_date=current)
        current = current + timedelta(days=1)

    write_csv(args.output, data)
    quit(0)