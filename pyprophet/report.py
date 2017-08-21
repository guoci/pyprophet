# needed for headless environment:

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

from scipy.stats import gaussian_kde
from numpy import linspace, concatenate, around


class Protein:

    def __init__(self, name):
        self.peptides = set()
        self.name = name

    def add_peptide(self, peptide):
        self.peptides.update([peptide])

    def get_concat_peptides(self):
        return "".join(self.peptides)


def save_report(report_path, prefix, decoys, targets, top_decoys, top_targets, cutoffs, svalues,
                qvalues, pvalues, pi0):

    if plt is None:
        raise ImportError("you need matplotlib package to create a report")

    plt.figure(figsize=(10, 15))
    plt.subplots_adjust(hspace=.5)

    plt.subplot(321)
    plt.title(prefix + "\n\nROC")
    plt.xlabel('false positive rate (q-value)')
    plt.ylabel('true positive rate (s-value)')

    plt.scatter(qvalues, svalues, s=3)
    plt.plot(qvalues, svalues)

    plt.subplot(322)
    plt.title('d-score performance')
    plt.xlabel('d-score cutoff')
    plt.ylabel('rates')

    plt.scatter(cutoffs, svalues, color='g', s=3)
    plt.plot(cutoffs, svalues, color='g', label="TPR (s-value)")
    plt.scatter(cutoffs, qvalues, color='r', s=3)
    plt.plot(cutoffs, qvalues, color='r', label="FPR (q-value)")

    plt.subplot(323)
    plt.title("top peak group d-score distributions")
    plt.xlabel("d-score")
    plt.ylabel("# of groups")
    plt.hist(
        [top_targets, top_decoys], 20, color=['g', 'r'], label=['target', 'decoy'], histtype='bar')
    plt.legend(loc=2)

    plt.subplot(324)
    tdensity = gaussian_kde(top_targets)
    tdensity.covariance_factor = lambda: .25
    tdensity._compute_covariance()
    ddensity = gaussian_kde(top_decoys)
    ddensity.covariance_factor = lambda: .25
    ddensity._compute_covariance()
    xs = linspace(min(concatenate((top_targets, top_decoys))), max(
        concatenate((top_targets, top_decoys))), 200)
    plt.title("top peak group d-score densities")
    plt.xlabel("d-score")
    plt.ylabel("density")
    plt.plot(xs, tdensity(xs), color='g', label='target')
    plt.plot(xs, ddensity(xs), color='r', label='decoy')
    plt.legend(loc=2)

    plt.subplot(325)
    if pvalues is not None:
        counts, __, __ = plt.hist(pvalues, bins=40, normed=True)
        plt.plot([0, 1], [pi0['pi0'], pi0['pi0']], "r")
        plt.title("p-value density histogram: pi0 = " + str(around(pi0['pi0'], decimals=3)))
        plt.xlabel("p-value")
        plt.ylabel("density histogram")

    if pi0['pi0_smooth'] is not False:
        plt.subplot(326)
        plt.plot(pi0['lambda_'], pi0['pi0_lambda'], ".")
        plt.plot(pi0['lambda_'], pi0['pi0_smooth'], "r")
        plt.xlim([0,1])
        plt.ylim([0,1])
        plt.title("pi0 smoothing fit plot")
        plt.xlabel("lambda")
        plt.ylabel("pi0est(lambda)")

    plt.savefig(report_path)

    return cutoffs, svalues, qvalues, top_targets, top_decoys


def mayu_cols():
    interesting_cols = ['run_id', 'transition_group_id', 'Sequence', 'ProteinName', 'm_score',
                        'Charge']
    return interesting_cols


def export_mayu(mayu_cutoff_file, mayu_fasta_file, mayu_csv_file, scored_table, final_stat):

    interesting_cols = mayu_cols()
    # write MAYU CSV input file
    mayu_csv = scored_table.df[scored_table.df["peak_group_rank"] == 1][interesting_cols]
    row_index = [str(i) for i in range(len(mayu_csv.index))]
    mayu_csv['Identifier'] = ("run" + mayu_csv['run_id'].astype('|S10') + "." + row_index
                              + "." + row_index + "." + mayu_csv['Charge'].astype('|S10'))
    mayu_csv['Mod'] = ''
    mayu_csv['m_score'] = 1 - mayu_csv['m_score']
    mayu_csv = mayu_csv[['Identifier', 'Sequence', 'ProteinName', 'Mod', 'm_score']]
    mayu_csv.columns = ['Identifier', 'Sequence', 'Protein', 'Mod', 'MScore']
    mayu_csv.to_csv(mayu_csv_file, sep=",", index=False)

    # write MAYU FASTA input file
    mayu_fasta = scored_table.df[scored_table.df["peak_group_rank"] == 1]
    mayu_fasta_file_out = open(mayu_fasta_file, "w")

    protein_dic = {}
    for entry in mayu_fasta[['ProteinName', 'Sequence']].iterrows():
        peptide = entry[1]['Sequence']
        protein = entry[1]['ProteinName']
        if protein not in protein_dic:
            p = Protein(protein)
            protein_dic[protein] = p
        protein_dic[protein].add_peptide(peptide)

    for k in protein_dic:
        protein = protein_dic[k]
        mayu_fasta_file_out.write(">%s\n" % protein.name)
        mayu_fasta_file_out.write(protein.get_concat_peptides())
        mayu_fasta_file_out.write("\n")

    # write MAYU cutoff input file
    mayu_cutoff = (final_stat.ix[0]['FP'] + final_stat.ix[0]['TN']) / \
                  (final_stat.ix[0]['TP'] + final_stat.ix[0]['FN']
                   + final_stat.ix[0]['FP'] + final_stat.ix[0]['TN'])

    mayu_cutoff_file_out = open(mayu_cutoff_file, "w")
    mayu_cutoff_file_out.write("%s" % mayu_cutoff)

    return True
