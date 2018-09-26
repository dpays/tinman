#!/usr/bin/env python3

from . import util

import argparse
import hashlib
import json
import subprocess
import sys

def process_esc(s, esc="", resolver=None):
    result = []
    for e, is_escaped in util.tag_escape_sequences(s, esc):
        if not is_escaped:
            result.append(e)
            continue
        ktype, seed = e.split(":", 1)
        if ktype == "publickey":
            result.append( json.dumps(resolver.get_pubkey(seed))[1:-1] )
        elif ktype == "privatekey":
            result.append( json.dumps(resolver.get_privkey(seed))[1:-1] )
        else:
            raise RuntimeError("invalid input")
    return "".join(result)

def compute_keypair_from_seed(seed, secret, get_dev_key_exe="get_dev_key"):
    result_bytes = subprocess.check_output([get_dev_key_exe, secret, seed])
    result_str = result_bytes.decode("utf-8")
    result_json = json.loads(result_str.strip())
    return (result_json[0]["public_key"], result_json[0]["private_key"])

class ProceduralKeyResolver(object):
    """
    Every synthetic testnet key is generated by concatenating the name, secret and role.
    This class is the central place these are issued, and keeps track of all of them.
    """
    def __init__(self, secret="", keyprefix="TST", get_dev_key_exe=""):
        self.seed2pair = {}
        self.secret = secret
        self.keyprefix = keyprefix
        self.get_dev_key_exe = get_dev_key_exe
        return

    def get(self, seed=""):
        pair = self.seed2pair.get(seed)
        if pair is None:
            pair = compute_keypair_from_seed(seed, self.secret, get_dev_key_exe=self.get_dev_key_exe)
            self.seed2pair[seed] = pair
        return pair

    def get_pubkey(self, seed):
        return self.get(seed)[0]

    def get_privkey(self, seed):
        return self.get(seed)[1]

def main(argv):
    parser = argparse.ArgumentParser(prog=argv[0], description="Resolve procedural keys")
    parser.add_argument("-i", "--input-file", default="-", dest="input_file", metavar="FILE", help="File to read actions from")
    parser.add_argument("-o", "--output-file", default="-", dest="output_file", metavar="FILE", help="File to write actions to")
    parser.add_argument("--get-dev-key", default="get_dev_key", dest="get_dev_key_exe", metavar="FILE", help="Specify path to get_dev_key tool")
    args = parser.parse_args(argv[1:])

    if args.output_file == "-":
        output_file = sys.stdout
    else:
        output_file = open(args.output_file, "w")

    if args.input_file == "-":
        input_file = sys.stdin
    else:
        input_file = open(args.input_file, "r")

    resolver = ProceduralKeyResolver(get_dev_key_exe=args.get_dev_key_exe)

    for line in input_file:
        line = line.strip()
        act, act_args = json.loads(line)
        if act == "set_secret":
            resolver.secret = act_args["secret"]
            continue
        esc = act_args.get("esc")
        if esc:
            act_args_minus_esc = dict(act_args)
            del act_args_minus_esc["esc"]
            json_line_minus_esc = json.dumps([act, act_args_minus_esc], separators=(",", ":"), sort_keys=True)
            line = process_esc(json_line_minus_esc, esc=esc, resolver=resolver)
        output_file.write(line)
        output_file.write("\n")
        output_file.flush()
    if args.input_file != "-":
        input_file.close()
    if args.output_file != "-":
        output_file.close()

if __name__ == "__main__":
    main(sys.argv)