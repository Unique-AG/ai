import os


import psycopg2
from psycopg2.extras import RealDictCursor
from unique_toolkit import LanguageModelMessages
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from pydantic import Field, create_model
from typing_extensions import override
from unique_toolkit.agentic.tools.agent_chunks_hanlder import AgentChunksHandler
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.chat.service import LanguageModelToolDescription
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelMessage,
    LanguageModelToolMessage,
)

from unique_toolkit.language_model.infos import (
    LanguageModelName,
)

from unique_toolkit.agentic.tools.schemas import BaseToolConfig

from db_tool_pm.prompts import (
    DEFAULT_TOOL_DESCRIPTION,
    DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
    DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT,
)

DB_HOST = os.getenv("PGHOST", "localhost")
DB_PORT = int(os.getenv("PGPORT", "10100"))
DB_NAME = os.getenv("PGDATABASE", "testdb")
DB_USER = os.getenv("PGUSER", "postgres")
DB_PASSWORD = os.getenv("PGPASSWORD", "postgres")

TABLE_NAME = "pm_positions"


class PMPositionsToolConfig(BaseToolConfig):
    pass


class PMPositionsTool(Tool[PMPositionsToolConfig]):
    name = "PM_Positions"

    @override
    def tool_description(self) -> LanguageModelToolDescription:
        db_tool_input = create_model(
            "PMPositionsToolInput",
            search_string=(
                str,
                Field(
                    description="Search string to find relevant information on stocks and instruments. This will be converted to sql and run against the database."
                ),
            ),
        )
        return LanguageModelToolDescription(
            name=self.name,
            description=DEFAULT_TOOL_DESCRIPTION,
            parameters=db_tool_input,
        )

    def tool_description_for_system_prompt(self) -> str:
        return DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT

    def tool_format_information_for_system_prompt(self) -> str:
        return DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return []

    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        query = tool_call.arguments["search_string"]  # type: ignore
        email = tool_call.arguments["email"]  # type: ignore
        conn = self.get_connection()
        where_clause = await self.run_llm_where_clause(
            conn=conn,
            natural_language_query=query,
        )
        print(where_clause)
        data = self.select_data(conn, where_clause, email)
        tool_response = ToolCallResponse(
            id=tool_call.id,  # type: ignore
            name=self.name,
            content=str(data),
            debug_info={
                "sql": f"SELECT * FROM (select * from {TABLE_NAME} where email= '{email}') as tmp {where_clause}"
            },
        )

        return tool_response

    async def run_llm_where_clause(self, conn, natural_language_query):
        system_prompt = self.build_system_prompt_for_sql_where(conn)

        messages = LanguageModelMessages.load_messages_to_root(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": natural_language_query},
            ]
        )

        response = await self._language_model_service.complete_async(
            model_name=LanguageModelName.AZURE_GPT_4o_2024_1120, messages=messages
        )
        print(response)
        return response.choices[0].message.content

    def get_connection(self):
        return psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        )

    def select_data(self, conn, where_clause, email):
        sql = f"SELECT * FROM (select * from {TABLE_NAME} where email= '{email}') as tmp {where_clause}"
        print(sql)
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            # colnames = [desc for desc in cur.description]
        # print(" | ".join(colnames))
        for r in rows:
            print(" | ".join(str(x) if x is not None else "" for x in r))
        return rows

    def get_column_descriptions(self, conn):
        sql_query = """
        SELECT
            column_name,
            data_type,
            is_nullable,
            character_maximum_length,
            numeric_precision,
            numeric_scale
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position;
        """
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql_query, (TABLE_NAME,))
            return cur.fetchall()

    def get_distinct_direction(self, conn):
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT DISTINCT direction FROM {TABLE_NAME} WHERE direction IS NOT NULL ORDER BY direction;"
            )
            result = [r for r in cur.fetchall()]
            return [r[0] for r in result]  # extract first element from each tuple

    def get_distinct_sleeve(self, conn):
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT DISTINCT sleeve FROM {TABLE_NAME} WHERE sleeve IS NOT NULL ORDER BY sleeve;"
            )
            result = [r for r in cur.fetchall()]
            return [r[0] for r in result]  # extract first element from each tuple

    def get_distinct_tickers(self, conn):
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT DISTINCT ticker FROM {TABLE_NAME} WHERE ticker IS NOT NULL ORDER BY ticker;"
            )
            result = [r for r in cur.fetchall()]
            return [r[0] for r in result]  # extract first element from each tuple

    def build_system_prompt_for_sql_where(self, conn):
        cols = self.get_column_descriptions(conn)
        direction = self.get_distinct_direction(
            conn
        )  # list is a list of tuples, take the first element of each tuple
        print(direction)
        tickers = self.get_distinct_tickers(conn)
        print(tickers)
        sleeve = self.get_distinct_sleeve(conn)
        print(sleeve)

        # Format column description lines
        col_lines = []
        for c in cols:
            name = c["column_name"]
            dtype = c["data_type"]
            is_nullable = c["is_nullable"]
            char_len = c["character_maximum_length"]
            num_prec = c["numeric_precision"]
            num_scale = c["numeric_scale"]

            type_str = dtype
            if char_len is not None:
                type_str += f"({char_len})"
            elif num_prec is not None:
                if num_scale is not None:
                    type_str += f"({num_prec},{num_scale})"
                else:
                    type_str += f"({num_prec})"
            nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
            col_lines.append(f"- {name}: {type_str} {nullable}")

        # Create prompt sections
        columns_section = "\n".join(col_lines)
        direction_section = ", ".join(sorted(direction))
        sleeve_section = ", ".join(sorted(sleeve))
        tickers_section = ", ".join(tickers)

        system_prompt = f"""
        You are a SQL generation assistant. Your sole output must be a valid SQL WHERE clause that can be appended to:
        SELECT * FROM {TABLE_NAME}
        The WHERE clause must reference only columns from the '{{TABLE_NAME}}' table.

        Strict rules:

        Output ONLY the SQL WHERE clause text (no SELECT, no comments, no explanations).
        Read-only retrieval ONLY. Do not generate INSERT/UPDATE/DELETE/DDL.
        Use standard PostgreSQL syntax.
        If no filtering is required, return 'WHERE TRUE'.
        Prefer safe comparisons (e.g., ILIKE for case-insensitive text matching when appropriate).
        For multiple conditions, use AND/OR with parentheses to be unambiguous.
        Use only columns listed in the "Columns" section below.
        When filtering by categorical fields (e.g., industry, ticker), use the allowed/known values sets below to avoid invalid values.
        Table: {TABLE_NAME}
        Columns:
        {columns_section}

        What the columns mean:
        Sleeve: Internal strategy bucket that the position belongs to (e.g., Rates, Equity L/S), used for risk budgeting and reporting.
        Ticker: The tradable symbol that uniquely identifies the security in markets (e.g., MSFT, IEF).
        Instrument: The type of security or contract (e.g., equity, future, swap, ETF) specifying economic and risk characteristics.
        Direction: Indicates whether the PM is long (benefits from price up) or short (benefits from price down) the instrument.
        Target Weight: The intended share of portfolio NAV to allocate to the position, typically set by the PM's sizing plan, with Target Weight=Target MVPortfolio NAV\\text\\{{Target Weight\\}} = \\frac\\{{\\text\\{{Target MV\\}}\\}}\\{{\\text\\{{Portfolio NAV\\}}\\}}Target Weight=Portfolio NAVTarget MV.
        Position: The current economic exposure or size held (e.g., quantity or dollar notional/market value), commonly Position (MV)=Quantity×Price\\text\\{{Position (MV)\\}} = \\text\\{{Quantity\\}} \\times \\text\\{{Price\\}}Position (MV)=Quantity×Price

        Allowed/known values:

        sleeve (DISTINCT): {sleeve_section}
        ticker (DISTINCT): {tickers_section}
        direction (DISTINCT): {direction_section}


        Examples of expected outputs:

        WHERE ticker = 'MSFT'
        WHERE direction = 'Long' AND target_weight >= 0.05
        WHERE (direction = 'Short') AND (position_mm < 0)
        WHERE ticker IN ('MSFT','JNJ','UNH') AND sleeve = 'Equity Long'
        WHERE instrument ILIKE '%Treasuries%' AND sleeve = 'Rates'
        WHERE (target_weight BETWEEN 0.03 AND 0.10) AND (position_mm >= 80)
        WHERE industry IN ('Technology','Financials')
        WHERE ticker ILIKE 'M%' OR instrument ILIKE '%ETF%'
        WHERE industry IS NOT NULL
        WHERE TRUE 


        When asked for unique categories like sleeve, tickers or direction, you should typically produce a WHERE clause that filters by those values (e.g., WHERE sleeve IN (...)) rather than listing them; however, use the allowed sets above to avoid invalid values.
        """

        return system_prompt

    def get_tool_call_result_for_loop_history(
        self,
        tool_response: ToolCallResponse,
        agent_chunks_handler: AgentChunksHandler,
    ) -> LanguageModelMessage:
        return LanguageModelToolMessage(
            content="{ }",
            tool_call_id=tool_response.id,  # type: ignore
            name=tool_response.name,
        )

    def get_evaluation_checks_based_on_tool_response(
        self, tool_response: ToolCallResponse
    ) -> list[EvaluationMetricName]:
        return []


ToolFactory.register_tool(PMPositionsTool, PMPositionsToolConfig)
