TRANSACTION_GENERATOR_EXCEPTION_LIMIT = 15
"""
The random transaction generator uses a set seed to generate transactions.
However, not all transactions are valid in all contexts. We catch illegal
generated transactions with a try/except, and retry until we generate a valid
one. However, if we exceed this limit, something is likely wrong with the generator
instead, due to the unlikely high number of exceptions.
"""

BENCHMARK_ITERATIONS = 5
BENCHMARK_ROUNDS = 3
