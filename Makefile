# Makefile for compiling Protocol Buffers

proto = hangups/hangouts.proto
proto_py = hangups/hangouts_pb2.py
proto_doc = docs/proto.rst
test_proto = hangups/test/test_pblite.proto
test_proto_py = hangups/test/test_pblite_pb2.py
venv_path = venv

all: $(proto_py) $(test_proto_py) $(proto_doc)

$(proto_py): $(proto)
	protoc --python_out . $(proto)

$(test_proto_py): $(test_proto)
	protoc --python_out . $(test_proto)

$(proto_doc): $(proto)
	python docs/generate_proto_docs.py $(proto) > $(proto_doc)

venv.build: .clean
	@rm -rf $(venv_path)
	@virtualenv $(venv_path)
	@$(venv_path)/bin/pip install -r requirements-dev.txt

test: .clean
	@$(venv_path)/bin/pip install -e ./
	@$(venv_path)/bin/pylint -j 4 ./hangups
	@$(venv_path)/bin/py.test -q ./hangups/test

.clean:
	@rm -rf `find . -name __pycache__`

clean:
	rm -f $(proto_py) $(proto_doc) $(test_proto_py)
