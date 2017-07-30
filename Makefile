##############################################################################
# General targets
##############################################################################

python = python3
venv = venv

.PHONY: venv
venv: venv-create venv-deps

.PHONY: venv-create
venv-create:
	$(python) -m venv --clear $(venv)

.PHONY: venv-deps
venv-deps:
	$(venv)/bin/pip install --upgrade pip
	$(venv)/bin/pip install --editable .
	$(venv)/bin/pip install --requirement requirements-dev.txt

.PHONY: test-all
test-all: style lint check test

.PHONY: style
style:
	$(venv)/bin/pycodestyle hangups

.PHONY: lint
lint:
	$(venv)/bin/pylint -j 4 --reports=n hangups

.PHONY: check
check:
	$(venv)/bin/python setup.py check --metadata --restructuredtext --strict

.PHONY: test
test:
	$(venv)/bin/pytest hangups

.PHONY: clean
clean:
	rm -rf $(venv) `find . -name __pycache__`

##############################################################################
# Protocol buffer targets
##############################################################################

proto = hangups/hangouts.proto
proto_py = hangups/hangouts_pb2.py
proto_doc = docs/proto.rst
test_proto = hangups/test/test_pblite.proto
test_proto_py = hangups/test/test_pblite_pb2.py

.PHONY: protos
protos: $(proto_py) $(test_proto_py) $(proto_doc)

.PHONY: clean-protos
clean-protos:
	rm -f $(proto_py) $(proto_doc) $(test_proto_py)

$(proto_py): $(proto)
	protoc --python_out . $(proto)

$(test_proto_py): $(test_proto)
	protoc --python_out . $(test_proto)

$(proto_doc): $(proto)
	$(venv)/bin/python docs/generate_proto_docs.py $(proto) > $(proto_doc)
