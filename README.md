# webnovel_downloader
Downloads Webnovels and creates epubs/html files

Supported Sites:

* Royalroad
* novelhall

To download:

    python download_webnovel.py -t epub,html <URL>

To See help:

    python download_webnovel.py --help

Help:

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
    #                  Webnovel Downloader v0.2                      #
    #              Supports royalroad and novelhall                  #
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
    # - Usage:
    # -    python download_webnovel.py [-t epub,html] [-s 100] [-o <PATH>] <URL-OF-SERIES>
    # -
    # - Arguments:
    # -    -t          Output format, e.g. html, epub. can contain multiple values, seperated by comma
    # -    -s <NUMBER> Split the novel into parts, the number after the parameter defines how many chapters each part has
    # -    -o <PATH>   Outputs novel to a specific path, use %i in the path when splitting the novel in seperate parts
    # -    --help      Displays this help
    # -
    # - Example:
    # -
    # -   python download_webnovel.py -s 100 -t epub -o "test\Test Part %i.epub" https://www.royalroad.com/fiction/12345/test