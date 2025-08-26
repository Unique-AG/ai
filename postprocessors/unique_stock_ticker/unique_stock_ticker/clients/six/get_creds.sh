#!/bin/bash

set -euo pipefail

show_usage() {
	cat <<EOF
Usage: $0 --cert|-c CERT_FILE --key|-k KEY_FILE [--output|-o OUTPUT_FILE]

Encode certificate and key files into a base64-encoded string

Options:
  -c, --cert CERT_FILE    Path to the certificate file
  -k, --key KEY_FILE      Path to the private key file  
  -o, --output OUTPUT_FILE Output file to write the result (if not specified, prints to stdout)
  -h, --help              Show this help message

Examples:
  $0 --cert cert.pem --key key.pem
  $0 -c /path/to/cert.crt -k /path/to/private.key
  $0 -c cert.pem -k key.pem -o encoded_creds.txt
EOF
}

get_creds() {
	local cert_path="$1"
	local key_path="$2"

	if [[ ! -f "$cert_path" ]]; then
		echo "Error: Certificate file not found: $cert_path" >&2
		exit 1
	fi

	if [[ ! -f "$key_path" ]]; then
		echo "Error: Key file not found: $key_path" >&2
		exit 1
	fi

	if ! cert_content=$(cat "$cert_path" 2>/dev/null); then
		echo "Error reading certificate file: $cert_path" >&2
		exit 1
	fi

	if ! key_content=$(cat "$key_path" 2>/dev/null); then
		echo "Error reading key file: $key_path" >&2
		exit 1
	fi

	cert_escaped=$(printf '%s' "$cert_content" | tr -d '\n')
	key_escaped=$(printf '%s' "$key_content" | tr -d '\n')

	content="[\"$cert_escaped\",\"$key_escaped\"]"
	echo -n "$content" | base64
}

cert_path=""
key_path=""
output_file=""

while [[ $# -gt 0 ]]; do
	case $1 in
	-c | --cert)
		cert_path="$2"
		shift 2
		;;
	-k | --key)
		key_path="$2"
		shift 2
		;;
	-o | --output)
		output_file="$2"
		shift 2
		;;
	-h | --help)
		show_usage
		exit 0
		;;
	*)
		echo "Error: Unknown option $1" >&2
		show_usage
		exit 1
		;;
	esac
done

if [[ -z "$cert_path" ]]; then
	echo "Error: Certificate file path is required" >&2
	show_usage
	exit 1
fi

if [[ -z "$key_path" ]]; then
	echo "Error: Key file path is required" >&2
	show_usage
	exit 1
fi

if ! encoded_creds=$(get_creds "$cert_path" "$key_path"); then
	echo "Error processing files" >&2
	exit 1
fi

if [[ -n "$output_file" ]]; then
	if ! echo "$encoded_creds" >"$output_file"; then
		echo "Error writing to output file: $output_file" >&2
		exit 1
	fi
	echo "Encoded credentials written to: $output_file"
else
	echo "$encoded_creds"
fi
