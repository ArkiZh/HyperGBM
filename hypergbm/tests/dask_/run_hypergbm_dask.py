# -*- coding:utf-8 -*-
"""

"""
from dask.distributed import Client

from hypergbm import make_experiment
from hypernets.tabular import dask_ex as dex
from hypernets.tabular.datasets import dsutils
from hypernets.tabular.metrics import calc_score


def main():
    # setup Dask cluster
    # client = Client("tcp://127.0.0.1:64958")
    # client = Client(processes=False, threads_per_worker=2, n_workers=1, memory_limit='4GB')
    client = Client(processes=True, threads_per_worker=4, n_workers=2, memory_limit='10GB')
    worker_count = len(client.ncores())
    print(client)

    # prepare data
    target_name = 'y'
    df = dsutils.load_bank_by_dask()
    # df = df.sample(frac=0.1)
    df = df.repartition(npartitions=worker_count)

    df_train, df_test = dex.train_test_split(df, test_size=0.5, random_state=42, shuffle=False)
    df_train, df_test = client.persist([df_train, df_test])

    # make experiment and run it
    experiment = make_experiment(df_train, target=target_name, log_level='info', down_sample_search=False)
    estimator = experiment.run(max_trials=30)
    best_trial = experiment.hyper_model.get_best_trial()
    print(f'best_trial: {best_trial}')

    # evaluate the trained estimator
    X_test = df_test.copy()
    y_test = X_test.pop(target_name)
    X_test, y_test = client.persist([X_test, y_test])
    y_pred = estimator.predict(X_test)
    y_proba = estimator.predict_proba(X_test)
    result = calc_score(y_test, y_pred, y_proba,
                        metrics=['accuracy', 'auc', 'logloss', 'f1', 'recall', 'precision'],
                        pos_label='yes')
    print(f'final result: {result}')


if __name__ == '__main__':
    main()
