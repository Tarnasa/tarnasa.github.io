# This makefile allows the easy generation of the website from templates,
#  as well git stuff

OBJECTS = grist/templates/* grist/posts/* alchemize.py

.PHONY: default all clean push

default: build

all: clean build push

build: index.html

clean:
	rm index.html
	rm -r posts

index.html: ${OBJECTS}
	python alchemize.py

push:
	git add ${OBJECTS}
	git commit
	git push origin master

