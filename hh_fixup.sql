
insert into offices
select 0+id, name, fax, address, notes
from Office;

insert into officers
select 0+id, name, email, office
from Officer;

insert into batches
select 0+id, name
from Batch;

insert into clients
select 0+id, name, ins, approval, dx, note, 0+officer
     , dob, address, phone, 0+batch
from Client;

insert into groups
select 0+id, Name
     , 0+substr(rate, length('USD $.'))
     , case Eval when 'Yes' then 1 else 0 end
from "Group";

insert into sessions
select 0+id 
     , substr(date, 7, 4) || '-' ||
       substr(date, 1, 2) || '-' ||
       substr(date, 4, 2)
     , 0+"group", time, therapist
from Session;

insert into visits
select 0+id, 0+session, 0+client, attend
     , 0+substr(client_pd, length('USD $.'))
     , note
     , substr(bill_date, 7, 4) || '-' ||
       substr(bill_date, 1, 2) || '-' ||
       substr(bill_date, 4, 2)
     , substr(check_date, 7, 4) || '-' ||
       substr(check_date, 1, 2) || '-' ||
       substr(check_date, 4, 2)
     , 0+substr("INS_PAID_$", length('USD $.'))
from Visit;
