# webnovel_downloader
Downloads Webnovels and creates epubs/html files

Supported Sites:

* Royalroad.com
* novelhall.com
* novelbin.me

To download:

    python download_webnovel.py -t epub,html <URL>

To See help:

    python download_webnovel.py --help

To update already downloaded Series

    python download_webnovel.py
	
	# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
    #                  Webnovel Downloader v0.2                      #
    #              Supports royalroad and novelhall                  #
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
    # - Output(s) selected: epub
    # - No valid URL provided
    # - Known books:
    #   * 0 - Amelia the Level Zero Hero
    #   * 1 - Infrasound Berserker
    #   * 2 - Path of the Last Champion [Sci-Fi LitRPG, Ancient System, Party Dynamics]
    #   * 3 - ShipCore
    #   * 4 - The Calamitous Bob
    #   * 5 - The Power of Ten
    #   * 6 - The Terran Traveller
    # - Choos from 0 to 6 to update one of the books, type c for cancel

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
	# -    --no-cache  Diables caching
    # -
    # - Example:
    # -
    # -   python download_webnovel.py -s 100 -t epub -o "test\Test Part %i.epub" https://www.royalroad.com/fiction/12345/test