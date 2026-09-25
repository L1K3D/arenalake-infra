import io
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from core.s3_mgr import get_s3_client
from core.security import get_current_user
from core.models import User

router = APIRouter()

class BiColumnsRequest(BaseModel):
    bucket: str
    filename: str

class VisualRequest(BaseModel):
    bucket: str
    filename: str
    tipo_grafico: str
    eixo_x: str = ""
    eixo_y: str = ""
    agregacao: str = ""
    eixo_z: str = ""
    colunas_tabela: list = []
    tema: str = "padrao"
    limite_linhas: int = 100
    ordenar_por: str = ""
    ordem: str = "asc"
    filtro_coluna: str = ""
    filtro_valor: str = ""

class FilterRequest(BaseModel):
    bucket: str
    filename: str
    coluna: str


@router.post("/bi/colunas")
async def get_bi_columns(req: BiColumnsRequest, current_user: User = Depends(get_current_user)):
    """Read only the schema of a CSV or Parquet object for BI selectors."""[cite: 23]
    try:
        s3_client = get_s3_client()
        obj = s3_client.get_object(Bucket=req.bucket, Key=req.filename)

        if req.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(obj["Body"].read()), nrows=0)
        else:
            df = pd.read_parquet(io.BytesIO(obj["Body"].read()))

        return JSONResponse(
            content={"status": "success", "colunas": df.columns.tolist()}
        )
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/bi/valores_coluna")
async def valores_coluna_bi(req: FilterRequest, current_user: User = Depends(get_current_user)):
    """Return sorted, non-null values from one dataset column for filtering."""[cite: 23]
    try:
        s3_client = get_s3_client()
        obj = s3_client.get_object(Bucket=req.bucket, Key=req.filename)
        df = (
            pd.read_csv(io.BytesIO(obj["Body"].read()), usecols=[req.coluna])
            if req.filename.endswith(".csv")
            else pd.read_parquet(io.BytesIO(obj["Body"].read()), columns=[req.coluna])
        )

        valores = df[req.coluna].dropna().unique().tolist()
        valores = sorted([str(v) for v in valores])
        return JSONResponse(content={"status": "success", "valores": valores})
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/bi/gerar_dados")
async def gerar_dados_bi(req: VisualRequest, current_user: User = Depends(get_current_user)):
    """Load a dataset and transform it into the requested visualization payload."""[cite: 23]
    try:
        s3_client = get_s3_client()
        obj = s3_client.get_object(Bucket=req.bucket, Key=req.filename)
        file_data = io.BytesIO(obj["Body"].read())

        cols_to_use = (
            req.colunas_tabela.copy()
            if req.tipo_grafico == "table"
            else [c for c in [req.eixo_x, req.eixo_y, req.eixo_z] if c]
        )

        if req.ordenar_por and req.ordenar_por not in cols_to_use:
            cols_to_use.append(req.ordenar_por)
        if req.filtro_coluna and req.filtro_coluna not in cols_to_use:
            cols_to_use.append(req.filtro_coluna)

        if req.filename.endswith(".csv"):
            df = pd.read_csv(file_data, usecols=cols_to_use)
        else:
            df = pd.read_parquet(file_data, columns=cols_to_use)

        if req.filtro_coluna and req.filtro_valor:
            df = df[df[req.filtro_coluna].astype(str) == str(req.filtro_valor)]

        df = df.dropna(
            subset=[
                c
                for c in cols_to_use
                if c != req.ordenar_por and c != req.filtro_coluna
            ]
        )

        if req.tipo_grafico == "table":
            if req.ordenar_por and req.ordenar_por in df.columns:
                df = df.sort_values(by=req.ordenar_por, ascending=(req.ordem == "asc"))

            df_table = df[req.colunas_tabela].head(req.limite_linhas)
            resposta = {
                "colunas": req.colunas_tabela,
                "linhas": df_table.astype(str).values.tolist(),
                "is_table": True,
                "tema": req.tema,
            }

        elif req.tipo_grafico == "kpi":
            if req.agregacao != "count":
                df[req.eixo_y] = pd.to_numeric(df[req.eixo_y], errors="coerce").fillna(0)

            if req.agregacao == "sum":
                valor = df[req.eixo_y].sum()
            elif req.agregacao == "avg":
                valor = df[req.eixo_y].mean()
            else:
                valor = df[req.eixo_y].count()

            resposta = {"valor": float(valor), "is_kpi": True, "tema": req.tema}

        elif req.tipo_grafico == "scatter":
            df[req.eixo_x] = pd.to_numeric(df[req.eixo_x], errors="coerce").fillna(0)
            df[req.eixo_y] = pd.to_numeric(df[req.eixo_y], errors="coerce").fillna(0)
            df_scatter = df.head(req.limite_linhas)

            if req.eixo_z:
                series_data = []
                for categoria, grupo in df_scatter.groupby(req.eixo_z):
                    pontos = grupo[[req.eixo_x, req.eixo_y]].values.tolist()
                    series_data.append({"name": str(categoria), "data": pontos})
                resposta = {"series": series_data, "is_scatter": True, "has_z": True}
            else:
                pontos = df_scatter[[req.eixo_x, req.eixo_y]].values.tolist()
                resposta = {
                    "series": [{"name": "Distribuição", "data": pontos}],
                    "is_scatter": True,
                    "has_z": False,
                }

        elif req.tipo_grafico == "matrix":
            if req.agregacao != "count":
                df[req.eixo_y] = pd.to_numeric(df[req.eixo_y], errors="coerce").fillna(0)

            if not req.eixo_z:
                df_agrupado = df.groupby(req.eixo_x)[req.eixo_y].count().reset_index()
                df_pivot = pd.DataFrame(
                    {req.eixo_y: df_agrupado[req.eixo_y].values},
                    index=df_agrupado[req.eixo_x].values,
                )
            else:
                if req.agregacao == "sum":
                    df_agg = df.groupby([req.eixo_x, req.eixo_z])[req.eixo_y].sum().reset_index()
                elif req.agregacao == "avg":
                    df_agg = df.groupby([req.eixo_x, req.eixo_z])[req.eixo_y].mean().reset_index()
                else:
                    df_agg = df.groupby([req.eixo_x, req.eixo_z])[req.eixo_y].count().reset_index()

                df_pivot = df_agg.pivot(
                    index=req.eixo_x, columns=req.eixo_z, values=req.eixo_y
                ).fillna(0)

            df_pivot = df_pivot.reset_index()

            if req.ordenar_por and req.ordenar_por in df_pivot.columns:
                df_pivot = df_pivot.sort_values(
                    by=req.ordenar_por, ascending=(req.ordem == "asc")
                )

            df_pivot = df_pivot.head(req.limite_linhas)
            cols_for_response = [str(c) for c in df_pivot.columns if c != req.eixo_x]

            resposta = {
                "colunas": cols_for_response,
                "index_nome": req.eixo_x,
                "linhas": df_pivot.astype(str).values.tolist(),
                "is_matrix": True,
                "tema": req.tema,
            }

        else:
            if req.agregacao != "count":
                df[req.eixo_y] = pd.to_numeric(df[req.eixo_y], errors="coerce").fillna(0)

            if req.eixo_z:
                if req.agregacao == "sum":
                    df_agrupado = df.groupby([req.eixo_x, req.eixo_z])[req.eixo_y].sum().reset_index()
                elif req.agregacao == "avg":
                    df_agrupado = df.groupby([req.eixo_x, req.eixo_z])[req.eixo_y].mean().reset_index()
                else:
                    df_agrupado = df.groupby([req.eixo_x, req.eixo_z])[req.eixo_y].count().reset_index()

                df_pivot = df_agrupado.pivot(
                    index=req.eixo_x, columns=req.eixo_z, values=req.eixo_y
                ).fillna(0)
                df_pivot = df_pivot.head(50)
                series_data = [
                    {"name": str(col), "data": df_pivot[col].tolist()}
                    for col in df_pivot.columns
                ]
                resposta = {
                    "categorias": df_pivot.index.astype(str).tolist(),
                    "series": series_data,
                    "is_stacked": True,
                }
            else:
                if req.agregacao == "sum":
                    df_agrupado = df.groupby(req.eixo_x)[req.eixo_y].sum().reset_index()
                elif req.agregacao == "avg":
                    df_agrupado = df.groupby(req.eixo_x)[req.eixo_y].mean().reset_index()
                else:
                    df_agrupado = df.groupby(req.eixo_x)[req.eixo_y].count().reset_index()

                df_agrupado = df_agrupado.head(50)
                resposta = {
                    "categorias": df_agrupado[req.eixo_x].astype(str).tolist(),
                    "valores": df_agrupado[req.eixo_y].tolist(),
                    "is_stacked": False,
                }

        return JSONResponse(content={"status": "success", "data": resposta})

    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)}, status_code=500
        )