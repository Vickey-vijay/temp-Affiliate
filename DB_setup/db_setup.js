// db_setup.js

// Switch to ramesh DB
db = db.getSiblingDB("ramesh");

// Create login_info if not exists
if (!db.getCollectionNames().includes("login_info")) {
    db.createCollection("login_info");
    db.login_info.insertOne({
        username: "admin",
        password: "admin123"  // hash this in production!
    });
    print("✅ login_info collection created.");
} else {
    print("ℹ️ login_info collection already exists.");
}

// Create products if not exists
if (!db.getCollectionNames().includes("products")) {
    db.createCollection("products");
    print("✅ products collection created.");
} else {
    print("ℹ️ products collection already exists.");
}

// Create published_data.products
const publishedDB = db.getMongo().getDB("published_data");
if (!publishedDB.getCollectionNames().includes("products")) {
    publishedDB.createCollection("products");
    print("✅ published_data.products collection created.");
} else {
    print("ℹ️ published_data.products already exists.");
}
