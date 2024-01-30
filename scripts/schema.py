from typing import List
from pydantic import BaseModel, Field

class OutputSchema(BaseModel):
    ticker: str = Field(
        default="<ticker>",
        description="The stock ticker symbol."
    )
    stock_rating: str = Field(
        default="<rating>; <analyst_rationale>",
        description="The stock rating and analyst rationale separated by semicolon (;). Stock ratings from analysts such as Buy, Strong Sell, Hold, Outperform, Overweight etc."
    )
    target_price: str = Field(
        default="<price>",
        description="The target stock price mentioned in documents."
    )
    sentiment: str = Field(
        default="<sentiment>",
        description="The NLP based sentiment towards the stock."
    )
    key_catalysts: List[str] = Field(
        default=[
            "<catalyst_1>; <comment>"
        ],
        description="List of top 4 key catalysts with comments separated by semicolon (;). Do not repeat kpis here. Provide qualitative metrics here"
    )
    key_kpis: List[str] = Field(
        default=[
            "<kpi_1>; <comment>",
        ],
        description="List of top 4 key performance indicators with comments separated by semicolon (;). Do not reapeat catalysts here. Provide quantitative metrics here"
    )
    portfolio_action: str = Field(
        default="<long_short_action>; <reason>",
        description="Portfolio action with reason separated by semicolon (;). Portfolio recommendations such as Add Long, Reduce Long, Close Long, Add Short, Reduce Short, Close Short etc."
    )
    broker_name: List[str] = Field(
        default=[
            "<source_1>",
        ],
        description="List of broker names as data sources."
    )
