# docker-park

Based on rroemhild/ejabberd.  Modified to run
github.com/punchagan/childrens-park.

Requires punchagan/park-storage to run.

## Usage

### Run park-storage first
```
$ docker run -i -t --name park-storage punchagan/park-storage
```

### Run in background

```
$ docker run -d -i -t --name park -p 5222:5222 -p 5269:5269 -p 5280:5280 -e "XMPP_DOMAIN=muse-amuse.in" --volumes-from=park-storage punchagan/park
```

## Exposed ports

* 5222
* 5269
* 5280

## Exposed volumes

* /opt/ejabberd/database
* /opt/ejabberd/ssl
* /opt/park