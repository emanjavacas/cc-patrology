
import subprocess
import argparse


start_from_help = """Where to start the process:
0: scrape vulgate
1: process vulgate
2: process source
3: tag source
4: extract source"""

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--source', help='path/to/dir with cc files')
    parser.add_argument('--start-from', type=int, default=0, help=start_from_help)
    parser.add_argument('--treetagger-dir')
    parser.add_argument('--pie-path')
    parser.add_argument('--device')
    args = parser.parse_args()

    # scrape vulgate
    if args.start_from <= 0:
        print("0 - scrape vulgate")
        subprocess.call(
            ['python', '-m', 'cc_patrology.plumbing.scrape_vulgate'])

    # process vulgate
    if args.start_from <= 1:
        print("1 - process vulgate")
        subprocess.call(
            ['python', '-m', 'cc_patrology.plumbing.process_vulgate',
             '--pie-path', args.pie_path, '--device', args.device,
             '--treetagger-dir', args.treetagger_dir])

    # process raw files
    if args.start_from <= 2:
        print("2 - process source")
        subprocess.call(
            ['python', '-m', 'cc_patrology.plumbing.process_source',
             args.source])

    # run tree-tagger to tokenize and tag files
    if args.start_from <= 3:
        print("3 - tag source")
        subprocess.call(
            ['bash', 'cc_patrology/plumbing/run_treetagger.sh',
             'output/tokenized', args.treetagger_dir, "latin.abbrv"])

    if args.start_from <= 4:
        # run python process_tokenized
        print("4 - extract source")
        subprocess.call(
            ['python', '-m', 'cc_patrology.plumbing.process_tokenized',
             '--pie-path', args.pie_path, '--device', args.device])
