# pat-caido
Project Archive Tool for Caido Workspaces

## I don't like deleting things.
I just don't. If I have the disk space and a good place to put something, I'll store it away for an unreasonable duration. Every once it a while it's interesting to revisit something ~~ancient~~ timeless, like the coursework I kept from an old embedded programming course or Debian 3.1r0 netinstall ISOs.

## I'd rather not have a continuously growing catch-all bucket.
Caido offers non-paid users two project slots. Initially my habitual behavior ended up with me having one project named "other" and one reasonably titled with whatever I was working on at the time, deleting once I was moving on to something else.

## These two points are at odds.
So I tossed together a tool that dumps some metadata and tgz's up a project. I'm doubting how much I'll be using the "restore" feature, but it's a tidy package I can keep locally, push to a NAS, and sync to a cloud for $6/TB/mo for that odd chance I need it again.

## Help?
Included is the help text as initially created. Recommended to always include -m, rarely use -p. I didn't continue to test the flags beyond using -m.

```
usage: pat-caido [-h] [-p] [-m] {list,archive,restore} [wsname]

Project Archive Tool for Caido Workspaces

positional arguments:
  {list,archive,restore}
  wsname

  options:
    -h, --help            show this help message and exit
    -p, --preserve        Preserve original content (do not delete workspace/archive)
    -m, --modify          Modify the Caido projects.db file to reflect changes
```
