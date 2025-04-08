import streamlit as st
import pymongo
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import io
import pymongo
from datetime import datetime
import time
from amazon_paapi import AmazonApi

client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["ramesh"]
collection = db["login_info"]
products_collection = db["products"]

# Amazon API Setup
ACCESS_KEY = "your_access_key"
SECRET_KEY = "your_secret_key"
ASSOCIATE_TAG = "your_associate_tag"
REGION = "us"  # Change to "in" for India, etc.


REQUIRED_COLUMNS = [
    "s_no","product_name","Product_unique_ID",
    "product_Affiliate_site","product_Affiliate_url",
    "product_major_category","product_minor_category",
    "Product_Buy_box_price","Product_lowest_price",
    "Product_current_price","Product_image_path",
    "Publish","Publish_time"
    ]


class LoginManager:
    def __init__(self, collection):
        self.collection = collection

    def authenticate(self, username, password):
        user = self.collection.find_one({"username": username, "password": password})
        return user is not None

class Publisher:
    def __init__(self, db_uri="mongodb://localhost:27017/", db_name="ramesh"):
        self.client = pymongo.MongoClient(db_uri)
        self.db = self.client[db_name]
        self.products_collection = self.db["products"]

        # Destination for successfully published entries
        self.published_db = self.client["published_data"]
        self.published_collection = self.published_db["products"]

    def telegram_push(self, product):
        # TODO: Replace with actual Telegram bot logic
        print(f"[Telegram] Publishing: {product['product_name']}")

    def whatsapp_push(self, product):
        # TODO: Replace with actual WhatsApp logic
        print(f"[WhatsApp] Publishing: {product['product_name']}")

    def run_scheduler(self):
        print("[Publisher] Scheduler started.")
        while True:
            now = datetime.now()

            # Find all products ready to publish
            scheduled_products = self.products_collection.find({
                "Publish": True,
                "Publish_time": {"$lte": now},
                "published_status": {"$ne": True}
            })

            for product in scheduled_products:
                try:
                    # 1. Push to Telegram and WhatsApp
                    self.telegram_push(product)
                    self.whatsapp_push(product)

                    # 2. Insert into published_data DB with published timestamp
                    product["published_at"] = now
                    self.published_collection.insert_one(product)

                    # 3. Update status in original products collection
                    self.products_collection.update_one(
                        {"_id": product["_id"]},
                        {"$set": {"published_status": True}}
                    )

                    print(f"[SUCCESS] Published {product['product_name']}")

                except Exception as e:
                    print(f"[ERROR] Could not publish {product.get('product_name', 'Unknown')}: {e}")

            time.sleep(30)  # Check every 30 seconds

class AmazonPriceExtractor:
    def __init__(self):
        self.amazon = AmazonApi(ACCESS_KEY, SECRET_KEY, ASSOCIATE_TAG, REGION)

    def fetch_prices(self, asin_list):
        try:
            products = self.amazon.get_items(asin_list)
            price_list = []
            for product in products.items:
                asin = product.asin
                price = (
                    product.prices.price.value
                    if product.prices and product.prices.price else "N/A"
                )
                price_list.append({"ASIN": asin, "Price": price, "Fetched_At": datetime.now()})
            return price_list
        except Exception as e:
            print("Error:", e)
            return []

    def extract_from_db_and_update(self):
        asins = products_collection.distinct("Product_unique_ID")
        prices = self.fetch_prices(asins)

        for product in prices:
            products_collection.update_one(
                {"Product_unique_ID": product["ASIN"]},
                {"$set": {"Product_current_price": product["Price"], "last_updated": product["Fetched_At"]}},
                upsert=False
            )

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
if "page" not in st.session_state:
    st.session_state.page = "Main Page"

def render_login_form(login_manager):
    st.title("🔐 Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if login_manager.authenticate(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("Login successful!")
                st.experimental_rerun()
            else:
                st.error("Invalid username or password")

def process_raw_data(df):
    df["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if "Publish_time" in df.columns:
        df["Publish_time"] = pd.to_datetime(df["Publish_time"], errors='coerce')

        # Convert NaT to None so MongoDB can handle it
        df["Publish_time"] = df["Publish_time"].apply(lambda x: x if pd.notnull(x) else None)

    return df

def amazon_extraction_page():
    st.header("📥 Amazon Product Extractor")
    st.write("Frequently used Amazon product extractor")

    frequency_hours = st.slider("Select extraction frequency (hours):", 1, 24, 6)
    last_run = st.session_state.get("last_run", None)

    if st.button("Run Price Extraction Now"):
        extractor = AmazonPriceExtractor()
        extractor.extract_from_db_and_update()
        st.success(f"✅ Extraction completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.session_state["last_run"] = datetime.now()

    # Auto-run if time elapsed exceeds frequency
    if last_run:
        elapsed = datetime.now() - last_run
        if elapsed >= timedelta(hours=frequency_hours):
            extractor = AmazonPriceExtractor()
            extractor.extract_from_db_and_update()
            st.session_state["last_run"] = datetime.now()
            st.info("⏱ Auto-extraction triggered based on set frequency.")

def clean_mongo_ready_row(row):
    for key, value in row.items():
        if isinstance(value, pd._libs.tslibs.nattype.NaTType):
            row[key] = None
    return row

def validate_columns(df):
    return set(REQUIRED_COLUMNS).issubset(df.columns)

def upload_to_mongo(df, collection):
    for _, row in df.iterrows():
        unique_id = row["Product_unique_ID"]
        collection.delete_one({"Product_unique_ID": unique_id})
        collection.insert_one(row.to_dict())

def extraction_page():
    st.header("📥 Upload Products excel! ")
    st.write("Upload your Excel file for processing:")

    uploaded_file = st.file_uploader(
        "Drag and drop file here",
        type=["xlsx", "xls"],
        accept_multiple_files=False,
        help="Limit 200MB per file • XLSX, XLS"
    )

    if uploaded_file:
        
            uploaded_df = pd.read_excel(uploaded_file)
            df = process_raw_data(uploaded_df)
            
            # Validate columns
            if not validate_columns(df):
                st.error("❌ Uploaded file does not match required columns.")
                st.code("\n".join(REQUIRED_COLUMNS))
                return
            
            # Display the data with enhanced preview
            st.success(f"✅ File validated successfully! Found {len(df)} products.")
            
            # Allow column filtering for preview
            if len(df) > 0:
                col_options = df.columns.tolist()
                selected_cols = st.multiselect(
                    "Select columns to preview", 
                    options=col_options,
                    default=["product_name", "Product_unique_ID", "product_major_category", "Product_current_price"]
                )
                
                if selected_cols:
                    st.dataframe(df[selected_cols])
                else:
                    st.dataframe(df)
            
            # Check for duplicates
            if "Product_unique_ID" in df.columns:
                # Check for duplicates within the file
                duplicate_ids = df[df.duplicated("Product_unique_ID", keep=False)]["Product_unique_ID"].unique()
                if len(duplicate_ids) > 0:
                    st.warning(f"⚠️ Found {len(duplicate_ids)} duplicated product IDs within this file.")
                    with st.expander("View duplicate products"):
                        st.dataframe(df[df["Product_unique_ID"].isin(duplicate_ids)])
                
                # Check for duplicates in the database
                products_collection = db["products"]
                existing_products = []
                
                for product_id in df["Product_unique_ID"].unique():
                    if products_collection.find_one({"Product_unique_ID": product_id}):
                        existing_products.append(product_id)
                
                if existing_products:
                    st.warning(f"⚠️ Found {len(existing_products)} products that already exist in the database.")
                    st.info("These products will be updated with the new data upon confirmation.")
            
            # Upload options
            st.subheader("Upload Options")
            upload_mode = st.radio(
                "Select upload mode:",
                ["Replace duplicates (default)", "Skip duplicates", "Append all (may create duplicates)"]
            )
            
            # Add option to set publish status and time for all products
            with st.expander("Batch settings (apply to all products)"):
                batch_publish = st.checkbox("Set publish status for all products")
                publish_status = st.checkbox("Publish", value=False, disabled=not batch_publish)
                
                batch_publish_time = st.checkbox("Set publish time for all products") 
                if batch_publish_time:
                    publish_date = st.date_input("Publish date")
                    publish_time = st.time_input("Publish time")
                    publish_datetime = datetime.combine(publish_date, publish_time)
                    publish_datetime = publish_datetime.replace(tzinfo=None)
                
                batch_category = st.checkbox("Set category for all products")
                if batch_category:
                    major_category = st.text_input("Major category")
                    minor_category = st.text_input("Minor category")
            
            # Upload to MongoDB
            if st.button("Confirm & Upload to DB"):
                products_collection = db["products"]
                
                # Apply batch settings if selected
                if batch_publish:
                    df["Publish"] = publish_status
                
                if batch_publish_time:
                    df["Publish_time"] = publish_datetime
                
                if batch_category:
                    if major_category:
                        df["product_major_category"] = major_category
                    if minor_category:
                        df["product_minor_category"] = minor_category
                
                with st.spinner("Uploading data to MongoDB..."):
                    if upload_mode == "Replace duplicates (default)":
                        for _, row in df.iterrows():
                            unique_id = row["Product_unique_ID"]
                            products_collection.delete_one({"Product_unique_ID": unique_id})
                            products_collection.insert_one(row.to_dict())
                        
                    elif upload_mode == "Skip duplicates":
                        skipped = 0
                        inserted = 0
                        for _, row in df.iterrows():
                            unique_id = row["Product_unique_ID"]
                            if not products_collection.find_one({"Product_unique_ID": unique_id}):
                                products_collection.insert_one(row.to_dict())
                                inserted += 1
                            else:
                                skipped += 1
                        st.info(f"Skipped {skipped} existing products, inserted {inserted} new products.")
                        
                    else:  
                        result = products_collection.insert_many([row.to_dict() for _, row in df.iterrows()])
                        st.info(f"Inserted {len(result.inserted_ids)} products.")
                
                st.success("🎉 Data uploaded to MongoDB successfully!")
                st.balloons()
    # st.header("📥Amazon Product Extractor")
    # st.write("Frequency used Amazon product extractor")
    amazon_extraction_page()

def manage_products_page():
    st.header("🛠️ Manage Products")
    products_collection = db["products"]

    products = list(products_collection.find({}))

    if not products:
        st.info("No products found.")
        return

    for product in products:
        with st.expander(f"📦 {product.get('product_name', 'Unnamed Product')}"):
            col1, col2 = st.columns(2)
            with col1:
                product_name = st.text_input("Product Name", value=product.get("product_name", ""), key=f"name_{product['_id']}")
                product_aff_url = st.text_input("Affiliate URL", value=product.get("product_Affiliate_url", ""), key=f"url_{product['_id']}")
                buy_price = st.text_input("Buy Box Price", value=(product.get("Product_Buy_box_price", "")), key=f"buy_{product['_id']}")
                low_price = st.text_input("Lowest Price", value=(product.get("Product_lowest_price", "")), key=f"low_{product['_id']}")
                current_price = st.text_input("Current Price", value=(product.get("Product_current_price", "")), key=f"current_{product['_id']}")

            with col2:
                major_cat = st.text_input("Major Category", value=product.get("product_major_category", ""), key=f"major_{product['_id']}")
                minor_cat = st.text_input("Minor Category", value=product.get("product_minor_category", ""), key=f"minor_{product['_id']}")
                image_path = st.text_input("Image Path", value=product.get("Product_image_path", ""), key=f"img_{product['_id']}")
                publish = st.checkbox("Publish", value=product.get("Publish", False), key=f"pub_{product['_id']}")
                pub_time = st.text_input("Publish Time", value=product.get("Publish_time", ""), key=f"ptime_{product['_id']}")

            if st.button("Save Changes", key=f"save_{product['_id']}"):
                updated_product = {
                    "product_name": product_name,
                    "product_Affiliate_url": product_aff_url,
                    "Product_Buy_box_price": buy_price,
                    "Product_lowest_price": low_price,
                    "Product_current_price": current_price,
                    "product_major_category": major_cat,
                    "product_minor_category": minor_cat,
                    "Product_image_path": image_path,
                    "Publish": publish,
                    "Publish_time": pub_time
                }
                products_collection.update_one(
                    {"Product_unique_ID": product["Product_unique_ID"]},
                    {"$set": updated_product}
                )
                st.success("✅ Product updated successfully!")
                st.experimental_rerun()

def configuration_page():
    st.header("⚙️ Configuration")
    st.write("Configure your app here.")

def product_search_page():
    st.header("🔍 Product Search")
    
    products_collection = db["products"]
    
    # Build search filters
    col1, col2 = st.columns(2)
    
    with col1:
        search_term = st.text_input("Search by product name or ID")
    
    with col2:
        search_category = st.selectbox(
            "Filter by category",
            options=["All Categories"] + list(set(
                p.get("product_major_category", "") 
                for p in products_collection.find({}, {"product_major_category": 1})
                if p.get("product_major_category")
            ))
        )
    
    col3, col4, col5 = st.columns(3)
    
    with col3:
        price_range = st.slider(
            "Price range",
            min_value=0.0,
            max_value=float(products_collection.find_one(
                sort=[("Product_current_price", -1)]
            ).get("Product_current_price", 10000)) if products_collection.count_documents({}) > 0 else 10000.0,
            value=(0.0, 5000.0),
            step=100.0
        )
    
    with col4:
        show_published = st.checkbox("Published products", value=True)
    
    with col5:
        show_unpublished = st.checkbox("Unpublished products", value=True)
    
    # Build query
    query = {}
    
    if search_term:
        query["$or"] = [
            {"product_name": {"$regex": search_term, "$options": "i"}},
            {"Product_unique_ID": {"$regex": search_term, "$options": "i"}}
        ]
    
    if search_category != "All Categories":
        query["product_major_category"] = search_category
    
    # Price range
    query["Product_current_price"] = {
        "$gte": str(price_range[0]),
        "$lte": str(price_range[1])
    }
    
    # Published status
    publish_conditions = []
    if show_published:
        publish_conditions.append({"published_status": True})
    if show_unpublished:
        publish_conditions.append({"published_status": False})
        publish_conditions.append({"published_status": {"$exists": False}})
    
    if publish_conditions:
        query["$or"] = query.get("$or", []) + publish_conditions
    
    # Execute search
    if st.button("Search"):
        results = list(products_collection.find(query))
        
        if not results:
            st.info("No products match your search criteria.")
        else:
            st.success(f"Found {len(results)} products matching your criteria.")
            
            # Display results
            for product in results:
                with st.expander(f"{product.get('product_name', 'Unknown')} ({product.get('Product_unique_ID', 'N/A')})"):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.subheader(product.get("product_name", "Unknown"))
                        st.write(f"**Category:** {product.get('product_major_category', 'N/A')} > {product.get('product_minor_category', 'N/A')}")
                        st.write(f"**Source:** {product.get('product_Affiliate_site', 'N/A')}")
                        if product.get("product_Affiliate_url"):
                            st.write(f"[Product Link]({product.get('product_Affiliate_url')})")
                    
                    with col2:
                        st.metric("Current Price", product.get("Product_current_price", "N/A"))
                        st.metric("Buy Box Price", product.get("Product_Buy_box_price", "N/A"))
                        st.metric("Lowest Price", product.get("Product_lowest_price", "N/A"))
                    
                    with col3:
                        published = product.get("published_status", False)
                        st.write(f"**Published:** {'Yes' if published else 'No'}")
                        if published and product.get("published_at"):
                            st.write(f"**Published At:** {product.get('published_at')}")
                        elif product.get("Publish") and product.get("Publish_time"):
                            st.write(f"**Scheduled For:** {product.get('Publish_time')}")
                        
                        # Quick actions
                        if not published:
                            if st.button("Publish Now", key=f"pub_{product['_id']}"):
                                # Import the Publisher class
                                # from publisher import Publisher
                                publisher = Publisher()
                                
                                try:
                                    publisher.telegram_push(product)
                                    publisher.whatsapp_push(product)
                                    
                                    # Update status
                                    products_collection.update_one(
                                        {"_id": product["_id"]},
                                        {"$set": {
                                            "published_status": True,
                                            "published_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        }}
                                    )
                                    
                                    # Add to published collection
                                    publisher.published_collection.insert_one({**product, "published_at": datetime.now()})
                                    
                                    st.success("Product published successfully!")
                                    st.experimental_rerun()
                                except Exception as e:
                                    st.error(f"Failed to publish: {str(e)}")
                        
                        if st.button("Edit", key=f"edit_{product['_id']}"):
                            st.session_state.page = "Manage Products"
                            st.session_state.edit_product_id = str(product["_id"])
                            st.experimental_rerun()

def summary_page():
    st.header("📊 Summary")
    st.write("Summary and reports will be displayed here.")

def publisher_control_page():
    st.header("📢 Publisher Control")
    
    # Import the Publisher class
    # from publisher import Publisher
    
    products_collection = db["products"]
    
    # Get all products scheduled for publishing
    scheduled_products = list(products_collection.find({
        "Publish": True,
        "published_status": {"$ne": True}
    }))
    
    st.subheader("Scheduled Publications")
    if not scheduled_products:
        st.info("No products are currently scheduled for publication.")
    else:
        st.write(f"**{len(scheduled_products)}** products scheduled for publication")
        
        # Create a dataframe for better display
        scheduled_df = pd.DataFrame([
            {
                "Product": p.get("product_name", "Unknown"),
                "Category": p.get("product_major_category", "N/A"),
                "Scheduled Time": p.get("Publish_time", "N/A"),
                "ID": p.get("Product_unique_ID", "N/A")
            } for p in scheduled_products
        ])
        
        st.dataframe(scheduled_df)
    
    # Manual publish controls
    st.subheader("Manual Publication")
    st.write("Select products to publish immediately:")
    
    # Get unpublished products
    unpublished_products = list(products_collection.find({
        "$or": [
            {"published_status": {"$ne": True}},
            {"published_status": {"$exists": False}}
        ]
    }))
    
    if not unpublished_products:
        st.info("No unpublished products available.")
    else:
        # Create selection for products
        product_options = {p.get("product_name", f"Unknown ({p.get('Product_unique_ID', 'N/A')})"):
                           p.get("Product_unique_ID", "") for p in unpublished_products}
        
        selected_products = st.multiselect(
            "Select products to publish",
            options=list(product_options.keys())
        )
        
        channels = st.multiselect(
            "Select channels",
            options=["Telegram", "WhatsApp"],
            default=["Telegram", "WhatsApp"]
        )
        
        if st.button("Publish Now", key="manual_publish"):
            if not selected_products:
                st.warning("Please select at least one product to publish")
            elif not channels:
                st.warning("Please select at least one channel")
            else:
                publisher = Publisher()
                success_count = 0
                
                for product_name in selected_products:
                    product_id = product_options[product_name]
                    product = products_collection.find_one({"Product_unique_ID": product_id})
                    
                    if not product:
                        st.error(f"Could not find product: {product_name}")
                        continue
                    
                    try:
                        if "Telegram" in channels:
                            publisher.telegram_push(product)
                        
                        if "WhatsApp" in channels:
                            publisher.whatsapp_push(product)
                        
                        # Update status
                        products_collection.update_one(
                            {"Product_unique_ID": product_id},
                            {"$set": {
                                "published_status": True,
                                "published_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }}
                        )
                        
                        # Add to published collection
                        publisher.published_collection.insert_one({**product, "published_at": datetime.now()})
                        
                        success_count += 1
                    except Exception as e:
                        st.error(f"Failed to publish {product_name}: {str(e)}")
                
                if success_count > 0:
                    st.success(f"Successfully published {success_count} products!")
                    st.balloons()
    
    # Publisher service status
    st.subheader("Publisher Service Status")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # This is mock functionality since we can't actually check the service status directly
        service_status = st.radio(
            "Publisher service:",
            ["Check status", "Start service", "Stop service"]
        )
        
        if service_status == "Check status":
            st.info("Publisher service status is simulated in this interface.")
        elif service_status == "Start service":
            st.success("Publisher service start command sent.")
            st.info("In a production environment, this would start the publisher.py script.")
        elif service_status == "Stop service":
            st.warning("Publisher service stop command sent.")
            st.info("In a production environment, this would stop the publisher.py script.")
    
    with col2:
        # Display logs (mock functionality)
        st.write("**Publisher Logs:**")
        st.code("""
[Publisher] Scheduler started.
[Publisher] Checking for scheduled publications...
[SUCCESS] Published Product ABC
[SUCCESS] Published Product XYZ
        """, language="text")

def dashboard_page():
    st.header("📊 Product Dashboard")
    
    products_collection = db["products"]
    products = list(products_collection.find({}))
    
    if not products:
        st.info("No products found to display in dashboard.")
        return

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    total_products = len(products)
    published_products = sum(1 for p in products if p.get("published_status", False))
    scheduled_products = sum(1 for p in products if p.get("Publish", False) and not p.get("published_status", False))
    
    with col1:
        st.metric("Total Products", total_products)
    with col2:
        st.metric("Published", published_products)
    with col3:
        st.metric("Scheduled", scheduled_products)
    with col4:
        unique_categories = len(set(p.get("product_major_category", "") for p in products))
        st.metric("Categories", unique_categories)
    
    # Category distribution
    st.subheader("Product Categories")
    categories = {}
    for product in products:
        category = product.get("product_major_category", "Uncategorized")
        categories[category] = categories.get(category, 0) + 1
    
    category_df = pd.DataFrame({
        "Category": list(categories.keys()),
        "Count": list(categories.values())
    })
    
    st.bar_chart(category_df.set_index("Category"))

    # Price analysis (last 5 modified products)
    st.subheader("Price Analysis (Last 5 Updated)")
    sorted_by_update = sorted(products, key=lambda x: x.get("updated_at", ""), reverse=True)
    recent_updated = sorted_by_update[:5]

    price_data = []
    for product in recent_updated:
        try:
            current_price = int(product.get("Product_current_price", 0) or 0)
            buy_box_price = int(product.get("Product_Buy_box_price", 0) or 0)
            lowest_price = int(product.get("Product_lowest_price", 0) or 0)

            
            price_data.append({
                "Product": product.get("product_name", "Unknown"),
                "Current Price": current_price,
                "Buy Box Price": buy_box_price,
                "Lowest Price": lowest_price
            })
        except (ValueError, TypeError):
            continue

    if price_data:
        price_df = pd.DataFrame(price_data)
        # st.dataframe(price_df.style.highlight_max(axis=0, subset=["Current Price", "Buy Box Price", "Lowest Price"]))
        st.dataframe(price_df)

    else:
        st.warning("No valid price data to display")

    # Recent uploads (last 5 added)
    st.subheader("Recently Added Products")
    recent_products = sorted(products, key=lambda x: x.get("created_at", ""), reverse=True)[:5]
    
    for product in recent_products:
        with st.expander(f"{product.get('product_name', 'Unknown')}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**ID:** {product.get('Product_unique_ID', 'N/A')}")
                st.write(f"**Category:** {product.get('product_major_category', 'N/A')} > {product.get('product_minor_category', 'N/A')}")
                st.write(f"**Price:** {product.get('Product_current_price', 'N/A')}")
            with col2:
                st.write(f"**Added:** {product.get('created_at', 'N/A')}")
                st.write(f"**Published:** {'Yes' if product.get('published_status', False) else 'No'}")
                st.write(f"**Affiliate:** {product.get('product_Affiliate_site', 'N/A')}")

def render_page():
    page = st.sidebar.radio(
        "📁 Pages",
        ["Dashboard", "Extraction", "Manage Products", "Product Search", "Publisher Control", "Configuration", "Summary"]
    )
    st.session_state.page = page
    
    if page == "Dashboard":
        dashboard_page()
    elif page == "Extraction":
        extraction_page()
    elif page == "Manage Products":
        manage_products_page()
    elif page == "Product Search":
        product_search_page()
    elif page == "Publisher Control":
        publisher_control_page()
    elif page == "Configuration":
        configuration_page()
    elif page == "Summary":
        summary_page()

def main():
    st.set_page_config(page_title="Product Management System", layout="centered")
    
    login_manager = LoginManager(collection)

    if not st.session_state.logged_in:
        render_login_form(login_manager)
    else:
        st.sidebar.success(f"Logged in as: {st.session_state.username}")
        
        # Add logout option
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.experimental_rerun()
            
        render_page()

if __name__ == "__main__":
    main()
