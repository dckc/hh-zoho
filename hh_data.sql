CREATE TABLE offices (
  id INTEGER PRIMARY KEY 
 ,   name TEXT 
 ,   fax TEXT 
 ,   address TEXT 
 ,   notes TEXT 
 );
CREATE TABLE officers (
  id INTEGER PRIMARY KEY 
 ,   name TEXT 
 ,   email TEXT 
 ,   office INTEGER 
 );
CREATE TABLE batches (
  id INTEGER PRIMARY KEY 
 ,   name TEXT 
 );
CREATE TABLE clients (
  id INTEGER PRIMARY KEY 
 ,   name TEXT 
 ,   ins TEXT 
 ,   approval TEXT 
 ,   DX TEXT 
 ,   note TEXT 
 ,   officer INTEGER 
 ,   DOB DATE 
 ,   address TEXT 
 ,   phone TEXT 
 ,   batch INTEGER 
 );
CREATE TABLE groups (
  id INTEGER PRIMARY KEY 
 ,   name TEXT 
 ,   rate NUMBER 
 ,   Eval INTEGER 
 );
CREATE TABLE sessions (
  id INTEGER PRIMARY KEY 
 ,   date DATE 
 ,   group_id INTEGER 
 ,   time TEXT 
 ,   therapist TEXT 
 );
CREATE TABLE visits (
  id INTEGER PRIMARY KEY 
 ,   session INTEGER 
 ,   client INTEGER 
 ,   attend INTEGER 
 ,   client_pd NUMBER 
 ,   note TEXT 
 ,   bill_date DATE 
 ,   check_date DATE 
 ,   ins_paid NUMBER 
 );
