from pyspark.sql import SparkSession

# Cria a sessão Spark (modo local)
spark = SparkSession.builder \
    .appName("ArenaLake-Primeiro-Job") \
    .master("local[*]") \
    .getOrCreate()

print(">>> Spark Session criada com sucesso")

# Dados de exemplo
dados = [
    ("Alice", 34),
    ("Bob", 45),
    ("Carol", 29),
    ("Daniel", 41)
]

df = spark.createDataFrame(dados, ["nome", "idade"])

print(">>> DataFrame criado")

# Mostra os dados
df.show()

# Operação simples
df_agg = df.groupBy().avg("idade")
df_agg.show()

spark.stop()
print(">>> Job finalizado com sucesso")