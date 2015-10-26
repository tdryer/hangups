# Makefile for compiling Protocol Buffers

proto = hangups/hangouts.proto
proto_py = hangups/hangouts_pb2.py
proto_doc = docs/proto.rst
test_proto = hangups/test/test_pblite.proto
test_proto_py = hangups/test/test_pblite_pb2.py

all: $(proto_py) $(test_proto_py) $(proto_doc)

$(proto_py): $(proto)
	protoc --python_out . $(proto)

$(test_proto_py): $(test_proto)
	protoc --python_out . $(test_proto)

$(proto_doc): $(proto)
	python docs/generate_proto_docs.py $(proto) > $(proto_doc)

clean:
	rm -f $(proto_py) $(proto_doc) $(test_proto_py)
