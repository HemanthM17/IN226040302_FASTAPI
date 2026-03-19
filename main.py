from fastapi import FastAPI, Query, Response, status, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

app = FastAPI()

products = [
    {"id": 1, "name": "Wireless Mouse",  "price": 499,  "category": "Electronics", "in_stock": True},
    {"id": 2, "name": "Notebook",        "price": 99,   "category": "Stationery",  "in_stock": True},
    {"id": 3, "name": "USB Hub",         "price": 799,  "category": "Electronics", "in_stock": False},
    {"id": 4, "name": "Pen Set",         "price": 49,   "category": "Stationery",  "in_stock": True},
]

orders        = []
feedback      = []
cart          = []
order_counter = 1


class NewProduct(BaseModel):
    name:     str  = Field(..., min_length=2, max_length=100)
    price:    int  = Field(..., gt=0)
    category: str  = Field(..., min_length=2)
    in_stock: bool = True

class OrderRequest(BaseModel):
    product_id:    int = Field(..., gt=0)
    quantity:      int = Field(..., gt=0)
    address:       str = Field(..., min_length=5)
    customer_name: str = Field(..., min_length=2)

class CustomerFeedback(BaseModel):
    customer_name: str           = Field(..., min_length=2, max_length=100)
    product_id:    int           = Field(..., gt=0)
    rating:        int           = Field(..., ge=1, le=5)
    comment:       Optional[str] = Field(None, max_length=300)

class OrderItem(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity:   int = Field(..., gt=0, le=50)

class BulkOrder(BaseModel):
    company_name:  str             = Field(..., min_length=2)
    contact_email: str             = Field(..., min_length=5)
    items:         List[OrderItem] = Field(..., min_items=1)

class CheckoutRequest(BaseModel):
    customer_name:    str = Field(..., min_length=2, max_length=100)
    delivery_address: str = Field(..., min_length=10)


def find_product(product_id: int):
    return next((p for p in products if p["id"] == product_id), None)


@app.get("/products")
def get_products():
    return {"products": products, "total": len(products)}


@app.get("/products/filter")
def filter_products(
    category:  str = Query(None, description="Filter by category"),
    max_price: int = Query(None, description="Maximum price"),
    min_price: int = Query(None, description="Minimum price"),
):
    result = products
    if category:
        result = [p for p in result if p["category"].lower() == category.lower()]
    if max_price is not None:
        result = [p for p in result if p["price"] <= max_price]
    if min_price is not None:
        result = [p for p in result if p["price"] >= min_price]
    return {"products": result, "count": len(result)}


@app.get("/products/search")
def search_products(keyword: str = Query(..., description="Search keyword")):
    result = [p for p in products if keyword.lower() in p["name"].lower()]
    if not result:
        return {"message": f"No products found for: {keyword}"}
    return {"keyword": keyword, "total_found": len(result), "products": result}


@app.get("/products/sort")
def sort_products(
    sort_by: str = Query("price", description="Sort by 'price' or 'name'"),
    order:   str = Query("asc",   description="'asc' or 'desc'"),
):
    if sort_by not in ["price", "name"]:
        return {"error": "sort_by must be 'price' or 'name'"}
    result = sorted(products, key=lambda p: p[sort_by], reverse=(order == "desc"))
    return {"sort_by": sort_by, "order": order, "products": result}


@app.get("/products/page")
def get_products_paged(
    page:  int = Query(1, ge=1,  description="Page number"),
    limit: int = Query(2, ge=1, le=20, description="Items per page"),
):
    start       = (page - 1) * limit
    paged       = products[start: start + limit]
    total_pages = -(-len(products) // limit)
    return {
        "page":        page,
        "limit":       limit,
        "total":       len(products),
        "total_pages": total_pages,
        "products":    paged,
    }


@app.get("/products/audit")
def product_audit():
    in_stock_list  = [p for p in products if     p["in_stock"]]
    out_stock_list = [p for p in products if not p["in_stock"]]
    stock_value    = sum(p["price"] * 10 for p in in_stock_list)
    priciest       = max(products, key=lambda p: p["price"])
    return {
        "total_products":     len(products),
        "in_stock_count":     len(in_stock_list),
        "out_of_stock_names": [p["name"] for p in out_stock_list],
        "total_stock_value":  stock_value,
        "most_expensive":     {"name": priciest["name"], "price": priciest["price"]},
    }


@app.put("/products/discount")
def bulk_discount(
    category:         str = Query(..., description="Category to discount"),
    discount_percent: int = Query(..., ge=1, le=99, description="Discount percentage (1-99)"),
):
    updated = []
    for p in products:
        if p["category"].lower() == category.lower():
            p["price"] = int(p["price"] * (1 - discount_percent / 100))
            updated.append({"id": p["id"], "name": p["name"], "new_price": p["price"]})
    if not updated:
        return {"message": f"No products found in category: {category}"}
    return {
        "message":          f"{discount_percent}% discount applied to {category}",
        "updated_count":    len(updated),
        "updated_products": updated,
    }


@app.get("/products/summary")
def product_summary():
    in_stock   = [p for p in products if     p["in_stock"]]
    out_stock  = [p for p in products if not p["in_stock"]]
    expensive  = max(products, key=lambda p: p["price"])
    cheapest   = min(products, key=lambda p: p["price"])
    categories = list(set(p["category"] for p in products))
    return {
        "total_products":     len(products),
        "in_stock_count":     len(in_stock),
        "out_of_stock_count": len(out_stock),
        "most_expensive":     {"name": expensive["name"], "price": expensive["price"]},
        "cheapest":           {"name": cheapest["name"],  "price": cheapest["price"]},
        "categories":         categories,
    }


@app.get("/products/sort-by-category")
def sort_by_category():
    result = sorted(products, key=lambda p: (p["category"], p["price"]))
    return {"products": result, "total": len(result)}


@app.get("/products/browse")
def browse_products(
    keyword: str = Query(None,    description="Search keyword"),
    sort_by: str = Query("price", description="Sort by 'price' or 'name'"),
    order:   str = Query("asc",   description="'asc' or 'desc'"),
    page:    int = Query(1,  ge=1,      description="Page number"),
    limit:   int = Query(4,  ge=1, le=20, description="Items per page"),
):
    result = products
    if keyword:
        result = [p for p in result if keyword.lower() in p["name"].lower()]
    if sort_by in ["price", "name"]:
        result = sorted(result, key=lambda p: p[sort_by], reverse=(order == "desc"))
    total       = len(result)
    start       = (page - 1) * limit
    paged       = result[start: start + limit]
    total_pages = -(- total // limit) if total > 0 else 0
    return {
        "keyword":     keyword,
        "sort_by":     sort_by,
        "order":       order,
        "page":        page,
        "limit":       limit,
        "total_found": total,
        "total_pages": total_pages,
        "products":    paged,
    }


@app.get("/products/{product_id}/price")
def get_product_price(product_id: int):
    product = find_product(product_id)
    if not product:
        return {"error": "Product not found"}
    return {"name": product["name"], "price": product["price"]}


@app.get("/products/{product_id}")
def get_product(product_id: int, response: Response):
    product = find_product(product_id)
    if not product:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "Product not found"}
    return {"product": product}


@app.post("/products", status_code=201)
def add_product(data: NewProduct, response: Response):
    if any(p["name"].lower() == data.name.lower() for p in products):
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"error": f"Product '{data.name}' already exists"}
    next_id = max(p["id"] for p in products) + 1
    new_product = {
        "id":       next_id,
        "name":     data.name,
        "price":    data.price,
        "category": data.category,
        "in_stock": data.in_stock,
    }
    products.append(new_product)
    return {"message": "Product added", "product": new_product}


@app.put("/products/{product_id}")
def update_product(
    product_id: int,
    response:   Response,
    price:      Optional[int]  = Query(None, gt=0, description="New price"),
    in_stock:   Optional[bool] = Query(None,        description="Stock status"),
):
    product = find_product(product_id)
    if not product:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "Product not found"}
    if price is not None:
        product["price"] = price
    if in_stock is not None:
        product["in_stock"] = in_stock
    return {"message": "Product updated", "product": product}


@app.delete("/products/{product_id}")
def delete_product(product_id: int, response: Response):
    product = find_product(product_id)
    if not product:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "Product not found"}
    products.remove(product)
    return {"message": f"Product '{product['name']}' deleted"}


@app.post("/feedback")
def submit_feedback(data: CustomerFeedback):
    feedback.append(data.dict())
    return {
        "message":        "Feedback submitted successfully",
        "feedback":       data.dict(),
        "total_feedback": len(feedback),
    }


@app.post("/orders")
def place_order(order: OrderRequest):
    global order_counter
    product = find_product(order.product_id)
    if not product:
        return {"error": "Product not found"}
    if not product["in_stock"]:
        return {"error": f"{product['name']} is out of stock"}
    new_order = {
        "order_id":      order_counter,
        "customer_name": order.customer_name,
        "product":       product["name"],
        "quantity":      order.quantity,
        "total":         product["price"] * order.quantity,
        "address":       order.address,
        "status":        "pending",
    }
    orders.append(new_order)
    order_counter += 1
    return {"message": "Order placed", "order": new_order}


@app.post("/orders/bulk")
def place_bulk_order(order: BulkOrder):
    confirmed, failed, grand_total = [], [], 0
    for item in order.items:
        product = find_product(item.product_id)
        if not product:
            failed.append({"product_id": item.product_id, "reason": "Product not found"})
        elif not product["in_stock"]:
            failed.append({"product_id": item.product_id, "reason": f"{product['name']} is out of stock"})
        else:
            subtotal = product["price"] * item.quantity
            grand_total += subtotal
            confirmed.append({"product": product["name"], "qty": item.quantity, "subtotal": subtotal})
    return {
        "company":     order.company_name,
        "confirmed":   confirmed,
        "failed":      failed,
        "grand_total": grand_total,
    }


@app.get("/orders/search")
def search_orders(customer_name: str = Query(..., description="Customer name to search")):
    result = [o for o in orders if customer_name.lower() in o["customer_name"].lower()]
    if not result:
        return {"message": f"No orders found for: {customer_name}"}
    return {"customer_name": customer_name, "total_found": len(result), "orders": result}


@app.get("/orders/page")
def get_orders_paged(
    page:  int = Query(1, ge=1,      description="Page number"),
    limit: int = Query(3, ge=1, le=20, description="Orders per page"),
):
    start       = (page - 1) * limit
    total_pages = -(-len(orders) // limit) if orders else 0
    return {
        "page":        page,
        "limit":       limit,
        "total":       len(orders),
        "total_pages": total_pages,
        "orders":      orders[start: start + limit],
    }


@app.get("/orders")
def get_orders():
    return {"orders": orders, "total_orders": len(orders)}


@app.get("/orders/{order_id}")
def get_order(order_id: int):
    for order in orders:
        if order["order_id"] == order_id:
            return {"order": order}
    return {"error": "Order not found"}


@app.patch("/orders/{order_id}/confirm")
def confirm_order(order_id: int):
    for order in orders:
        if order["order_id"] == order_id:
            order["status"] = "confirmed"
            return {"message": "Order confirmed", "order": order}
    return {"error": "Order not found"}


@app.post("/cart/add")
def add_to_cart(
    product_id: int = Query(..., gt=0, description="Product ID to add"),
    quantity:   int = Query(1,  gt=0,  description="Quantity to add"),
):
    product = find_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if not product["in_stock"]:
        raise HTTPException(status_code=400, detail=f"{product['name']} is out of stock")
    for item in cart:
        if item["product_id"] == product_id:
            item["quantity"] += quantity
            item["subtotal"]  = item["unit_price"] * item["quantity"]
            return {"message": "Cart updated", "cart_item": item}
    cart_item = {
        "product_id":   product_id,
        "product_name": product["name"],
        "quantity":     quantity,
        "unit_price":   product["price"],
        "subtotal":     product["price"] * quantity,
    }
    cart.append(cart_item)
    return {"message": "Added to cart", "cart_item": cart_item}


@app.get("/cart")
def get_cart():
    if not cart:
        return {"message": "Cart is empty"}
    grand_total = sum(item["subtotal"] for item in cart)
    return {"items": cart, "item_count": len(cart), "grand_total": grand_total}


@app.delete("/cart/{product_id}")
def remove_from_cart(product_id: int):
    for item in cart:
        if item["product_id"] == product_id:
            cart.remove(item)
            return {"message": f"{item['product_name']} removed from cart"}
    raise HTTPException(status_code=404, detail="Product not found in cart")


@app.post("/cart/checkout")
def checkout(data: CheckoutRequest):
    global order_counter
    if not cart:
        raise HTTPException(status_code=400, detail="Cart is empty — add items first")
    orders_placed = []
    grand_total   = 0
    for item in cart:
        new_order = {
            "order_id":         order_counter,
            "customer_name":    data.customer_name,
            "product":          item["product_name"],
            "quantity":         item["quantity"],
            "total_price":      item["subtotal"],
            "delivery_address": data.delivery_address,
            "status":           "confirmed",
        }
        orders.append(new_order)
        orders_placed.append(new_order)
        grand_total   += item["subtotal"]
        order_counter += 1
    cart.clear()
    return {
        "message":       "Checkout successful",
        "customer_name": data.customer_name,
        "orders_placed": orders_placed,
        "grand_total":   grand_total,
    }