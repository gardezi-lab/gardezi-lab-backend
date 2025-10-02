from flask import request

def paginate_query(cursor, base_query, params=()):
    #  Page number frontend se (default = 1)
    page = request.args.get('page', 1, type=int)

    #  Page size frontend se (default = 10)
    page_size = request.args.get('page_size', 10, type=int)

    #  Safety checks (optional)
    if page_size <= 0:
        page_size = 10
    elif page_size > 100:  # Max limit to avoid abuse
        page_size = 100

    #  Offset calculate
    offset = (page - 1) * page_size

    #  Total records count
    count_query = f"SELECT COUNT(*) AS total FROM ({base_query}) AS total_table"
    cursor.execute(count_query, params)
    total_records = cursor.fetchone()[0]

    #  Paginated data
    paginated_query = f"{base_query} LIMIT %s OFFSET %s"
    cursor.execute(paginated_query, params + (page_size, offset))
    rows = cursor.fetchall()

    #  Convert rows → list of dicts
    column_names = [desc[0] for desc in cursor.description]
    data = [dict(zip(column_names, row)) for row in rows]

    #  Total pages
    total_pages = (total_records + page_size - 1) // page_size

    return {
        "data": data,
        "pagination": {
            "total_records": total_records,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }
