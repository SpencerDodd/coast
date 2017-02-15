# coast
Coast is a torrent client implementing the [BitTorrent protocol](https://wiki.theory.org/BitTorrentSpecification).

This project has been a learning experience for me in how torrenting works at a low level, and managing multiple
network-interactive objects using the [Twisted framework](https://twistedmatrix.com/trac/).

### Notes
Does not support multiple file mode yet. So only individual files can be downloaded (.iso, .mp4, etc), not albums or
directories of files.

Does not support UDP tracker interaction.

Does not support ipv6.

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
