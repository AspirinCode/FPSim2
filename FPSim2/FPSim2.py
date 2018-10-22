import multiprocessing as mp
import concurrent.futures as cf
from .FPSim2lib import similarity_search, in_memory_ss
from .io import tables, load_query, COEFFS
from operator import itemgetter
import time


def run_search(query, fp_filename, threshold=0.7, coeff='tanimoto', chunk_size=1000000, n_threads=mp.cpu_count()):
    with tables.open_file(fp_filename, mode='r') as fp_file:
        n_mols = fp_file.root.fps.shape[0]
        fp_tpye = fp_file.root.config[0]

    query = load_query(query, fp_filename)

    if coeff == 'substructure':
         # if substructure automatically set threshold to 1.0
        threshold = 1.0
        if fp_tpye != 'RDKPatternFingerprint':
            print('Warning: Running a substructure search with {} fingerprints. '
                'Consider using RDKPatternFingerprint'.format(fp_tpye))

    # chunkify
    c_indexes =((x, x + chunk_size) for x in range(0, n_mols, chunk_size))
    results = []
    with cf.ProcessPoolExecutor(max_workers=n_threads) as ppe:
        future_ss = {ppe.submit(similarity_search, query, fp_filename, indexes, threshold, COEFFS[coeff]): 
                        c_id for c_id, indexes in enumerate(c_indexes)}
        for future in cf.as_completed(future_ss):
            m = future_ss[future]
            try:
                res = future.result()
                results.append(res)
            except Exception as e:
                print('Chunk {} thread died: '.format(m), e)
    # flatten results
    res = [item for sublist in results for item in sublist]
    return sorted(res, key=itemgetter(1), reverse=True)


def run_in_memory_search(query, fps, threshold=0.7, coeff='tanimoto', n_threads=mp.cpu_count()):
    results = []
    with cf.ThreadPoolExecutor(max_workers=n_threads) as tpe:
        future_ss = {tpe.submit(in_memory_ss, query, chunk, threshold, COEFFS[coeff]): 
                        c_id for c_id, chunk in enumerate(fps)}
        for future in cf.as_completed(future_ss):
            m = future_ss[future]
            try:
                res = future.result()
                results.append(res)
            except Exception as e:
                print('Chunk {} thread died: '.format(m), e)
    res = [item for sublist in results for item in sublist]
    return sorted(res, key=itemgetter(1), reverse=True)