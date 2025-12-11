from sqlite import create_connection, create_table


download_values = [
    "url text NOT NULL",
    "downloader text NOT NULL",
    "download_status text NOT NULL",
    "start_date DATE",
    "end_date DATE",
    "time_elapsed text",
    "output_path text",
    "source_url text",
    "proxy text",
    "extra_args text",
    "PRIMARY KEY (url, output_path)",
]

downloader_values = [
    "downloader_type text NOT NULL",
    "downloader_path text",
    "module text NOT NULL",
    "func text NOT NULL",
    "downloader_args text",
    "PRIMARY KEY (downloader_type)",
]

tables = ["downloads", "downloaders"]
values = [download_values, downloader_values]


def create_db(db_path: str, tables: list = tables, values: list = values):

    conn = create_connection(db_path)

    # create tables
    for t, v in zip(tables, values):
        create_table(conn, t, v)

    return conn
