const { Client } = require('pg');
require('dotenv').config();

const config = {
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    host: process.env.DB_HOST,
    port: process.env.DB_PORT,
};

const setup = async () => {
    // 1. Connect to default 'postgres' database to create the new DB
    const client1 = new Client({
        ...config,
        database: 'postgres',
    });

    try {
        await client1.connect();
        
        // Check if database exists
        const res = await client1.query("SELECT 1 FROM pg_database WHERE datname = 'stock_management'");
        if (res.rowCount === 0) {
            console.log("Creating database 'stock_management'...");
            await client1.query('CREATE DATABASE stock_management');
            console.log("Database created.");
        } else {
            console.log("Database 'stock_management' already exists.");
        }
    } catch (err) {
        console.error("Error creating database:", err.message);
    } finally {
        await client1.end();
    }

    // 2. Connect to the new 'stock_management' database to create tables
    const client2 = new Client({
        ...config,
        database: 'stock_management',
    });

    try {
        await client2.connect();
        console.log("Connected to 'stock_management'. Setting up tables...");

        // Create Products Table
        await client2.query(`
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                reference VARCHAR(255),
                description TEXT NOT NULL,
                quantity INTEGER DEFAULT 0,
                unit_price DECIMAL(10, 2),
                unit VARCHAR(50),
                category VARCHAR(100),
                full_stock_value DECIMAL(12, 2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        `);
        console.log("Table 'products' verified/created.");

        // Create Invoices Table
        await client2.query(`
            CREATE TABLE IF NOT EXISTS invoices (
                id SERIAL PRIMARY KEY,
                invoice_number VARCHAR(100),
                buyer_name VARCHAR(255),
                total_amount DECIMAL(12, 2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        `);
        console.log("Table 'invoices' verified/created.");

        console.log("✅ Setup complete!");
    } catch (err) {
        console.error("Error setting up tables:", err.message);
    } finally {
        await client2.end();
    }
};

setup();
