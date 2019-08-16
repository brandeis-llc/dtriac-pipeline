from sys import argv 
import json

with open(argv[1]) as infile:
    lif = {"discriminator": "http://vocab.lappsgrid.org/ns/media/jsonld#lif",
            "payload": { 
                "@context": "http://vocab.lappsgrid.org/context-1.0.0.jsonld",
                "metadata": {},
                "text": {
                    "@value": infile.read(),
                    "@language": "en"
                    },
                "views": []
                }
            }
    print(json.dumps(lif))

