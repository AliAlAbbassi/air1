create or replace function update_updated_on_column()
    returns trigger as
$$
begin
    new.updated_on = now();
    return new;
end;
$$ language plpgsql;