# Makefile for compiling Protocol Buffers

all: hangups/test/test_pblite_pb2.py hangups/hangouts_pb2.py

hangups/test/test_pblite_pb2.py: hangups/test/test_pblite.proto
	protoc --python_out . hangups/test/test_pblite.proto

hangups/hangouts_pb2.py: hangups/hangouts.proto
	protoc --python_out . hangups/hangouts.proto
