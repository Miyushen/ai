import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.db.base import Base, SessionLocal, engine
from app.db.models import (
    Customer,
    DailyTraffic,
    MarketingCampaign,
    MetricDefinition,
    Order,
    OrderItem,
    Product,
    Refund,
)

RNG = random.Random(20261102)
END_DATE = date(2026, 10, 31)
START_DATE = END_DATE - timedelta(days=179)
REGIONS = ["North", "East", "South", "West"]
CHANNELS = ["Organic", "Paid Search", "Marketplace", "Direct"]
CATEGORIES = ["Electronics", "Home", "Sports", "Beauty", "Books"]


def money(value: float) -> Decimal:
    return Decimal(f"{value:.2f}")


def seed_database() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        if session.scalar(select(func.count(Customer.id))):
            print("Database already seeded; skipping.")
            return

        customers = [
            Customer(
                name=f"Customer {index:04d}",
                region=RNG.choice(REGIONS),
                signup_date=START_DATE - timedelta(days=RNG.randint(0, 540)),
            )
            for index in range(1, 501)
        ]
        session.add_all(customers)

        products: list[Product] = []
        for index in range(1, 51):
            category = CATEGORIES[(index - 1) % len(CATEGORIES)]
            cost = RNG.uniform(8, 320) * (1.7 if category == "Electronics" else 1)
            products.append(
                Product(
                    name=f"{category} Product {index:02d}",
                    category=category,
                    unit_cost=money(cost),
                    list_price=money(cost * RNG.uniform(1.35, 2.1)),
                )
            )
        session.add_all(products)
        session.flush()

        metric_definitions = [
            MetricDefinition(
                metric_name="revenue",
                formula="SUM(order_items.quantity * order_items.unit_price * (1 - order_items.discount))",
                description="Gross merchandise revenue before refunds.",
            ),
            MetricDefinition(
                metric_name="net_revenue",
                formula="revenue - SUM(refunds.amount)",
                description="Revenue after subtracting refunded amounts.",
            ),
            MetricDefinition(
                metric_name="gross_profit",
                formula="net_revenue - SUM(order_items.quantity * products.unit_cost)",
                description="Net revenue minus product cost; excludes ad spend.",
            ),
            MetricDefinition(
                metric_name="refund_rate",
                formula="refunded_order_items / total_order_items",
                description="Share of order items that received a refund.",
            ),
        ]
        session.add_all(metric_definitions)

        daily_traffic: list[DailyTraffic] = []
        for day_offset in range(180):
            event_date = START_DATE + timedelta(days=day_offset)
            for channel in CHANNELS:
                visits = RNG.randint(500, 1400)
                spend = 0.0 if channel in {"Organic", "Direct"} else RNG.uniform(300, 900)
                if channel == "Paid Search" and event_date >= END_DATE - timedelta(days=29):
                    spend *= 1.8
                    visits = int(visits * 1.08)
                daily_traffic.append(
                    DailyTraffic(
                        event_date=event_date,
                        channel=channel,
                        visits=visits,
                        ad_spend=money(spend),
                    )
                )
        session.add_all(daily_traffic)

        session.add_all(
            [
                MarketingCampaign(
                    name="Autumn Search Push",
                    channel="Paid Search",
                    start_date=END_DATE - timedelta(days=29),
                    end_date=END_DATE,
                    spend=money(32_000),
                ),
                MarketingCampaign(
                    name="Marketplace Midyear Sale",
                    channel="Marketplace",
                    start_date=START_DATE + timedelta(days=50),
                    end_date=START_DATE + timedelta(days=64),
                    spend=money(12_500),
                ),
            ]
        )

        session.flush()
        customer_ids = [customer.id for customer in customers]
        product_ids = [product.id for product in products]
        product_by_id = {product.id: product for product in products}

        order_items: list[OrderItem] = []
        for index in range(1, 5001):
            order_date = START_DATE + timedelta(days=RNG.randint(0, 179))
            customer = customers[RNG.randrange(len(customers))]
            # North-region demand drops by roughly 45% in the final month.
            if customer.region == "North" and order_date >= END_DATE - timedelta(days=29):
                if RNG.random() < 0.45:
                    customer = customers[RNG.randrange(len(customers))]
            order = Order(
                customer_id=customer.id,
                order_date=order_date,
                channel=RNG.choices(CHANNELS, weights=[30, 25, 25, 20], k=1)[0],
                status=RNG.choices(["completed", "cancelled"], weights=[96, 4], k=1)[0],
            )
            session.add(order)
            session.flush()

            for _ in range(RNG.randint(1, 4)):
                product = product_by_id[RNG.choice(product_ids)]
                discount = RNG.choice([0, 0, 0.05, 0.1, 0.15])
                item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=RNG.randint(1, 3),
                    unit_price=product.list_price,
                    discount=Decimal(str(discount)),
                )
                session.add(item)
                order_items.append(item)

        session.flush()
        refund_reasons = ["damaged", "not as described", "late delivery", "changed mind"]
        refunds: list[Refund] = []
        for item in order_items:
            product = product_by_id[item.product_id]
            order = session.get(Order, item.order_id)
            probability = 0.035
            if product.category == "Electronics" and order and order.order_date >= END_DATE - timedelta(days=44):
                probability = 0.18
            if RNG.random() < probability:
                gross = float(item.quantity * item.unit_price * (Decimal("1") - item.discount))
                refunds.append(
                    Refund(
                        order_item_id=item.id,
                        refund_date=min(END_DATE, order.order_date + timedelta(days=RNG.randint(2, 14))),
                        amount=money(gross * RNG.uniform(0.7, 1.0)),
                        reason=RNG.choice(refund_reasons),
                    )
                )
        session.add_all(refunds)
        session.commit()
        print(
            f"Seeded {len(customers)} customers, {len(products)} products, "
            f"5000 orders, {len(order_items)} items, and {len(refunds)} refunds."
        )


if __name__ == "__main__":
    seed_database()
