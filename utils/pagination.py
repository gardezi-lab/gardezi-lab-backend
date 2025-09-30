from flask import request

def paginate_query(cursor, base_query, params=(), page_size=10):
    page = request.args.get('page', 1, type=int)
    offset = (page - 1) * page_size

    # Count total records
    count_query = f"SELECT COUNT(*) AS total FROM ({base_query}) AS total_table"
    cursor.execute(count_query, params)
    count_row = cursor.fetchone()

    if count_row is None:
        total_records = 0
    elif isinstance(count_row, dict):
        total_records = count_row["total"]
    else:
        total_records = count_row[0]

    # Paginate data
    paginated_query = f"{base_query} LIMIT %s OFFSET %s"
    cursor.execute(paginated_query, params + (page_size, offset))
    rows = cursor.fetchall()
    column_names = [desc[0] for desc in cursor.description]
    data = [dict(zip(column_names, row)) for row in rows]

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

