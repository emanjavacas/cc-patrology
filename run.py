
import subprocess
import argparse

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--source', help='path/to/dir with cc files')
    parser.add_argument('--treetagger-dir')
    parser.add_argument('--pie-path')
    parser.add_argument('--device')
    args = parser.parse_args()

    # scrape vulgate
    subprocess.call(
        ['python', '-m', 'cc_patrology.plumbing.scrape_vulgate'])

    # process vulgate
    subprocess.call(
        ['python', '-m', 'cc_patrology.plumbing.process_vulgate',
         '--pie-path', args.pie_path, '--device', args.device,
         '--treetagger-dir', args.treetagger_dir])

    # process raw files
    subprocess.call(
        ['python', '-m', 'cc_patrology.plumbing.process_source',
         args.source])

    # run tree-tagger to tokenize and tag files
    subprocess.call(
        ['bash', 'cc_patrology/plumbing/run_treetagger.sh',
         'output/tokenized', args.treetagger_dir, "latin.abbrv"])

    # run python process_tokenized
    subprocess.call(
        ['python', '-m', 'cc_patrology.plumbing.process_tokenized',
         '--pie-path', args.pie_path, '--device', args.device])
