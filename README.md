# coast
Coast is a torrent client implementing the [BitTorrent protocol](https://wiki.theory.org/BitTorrentSpecification).

This project has been a learning experience for me in how torrenting works at a low level, and managing multiple
network-interactive objects using the [Twisted framework](https://twistedmatrix.com/trac/).

### Usage
Clone the repo
```
git clone https://github.com/spencerdodd/coast
cd coast
```
Install the required packages
```
pip install -r requirements.txt
```
Run the core in either commandline or GUI mode
```
core.py -m <mode> [cmd | gui]
```

That should be it!
