SHELL=/bin/bash

.PHONY: protobuf
# Recompile Protobufs for Python
protobuf:
	@# Python protobuf generation
	protoc \
		--proto_path=proto \
		--python_out=src/plots/proto \
		proto/*.proto


.PHONY: clean
# Remove all generated files.
clean:
	rm -f src/plots/proto/*_pb2.py*