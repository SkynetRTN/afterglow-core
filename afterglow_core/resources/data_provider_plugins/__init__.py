"""
Afterglow Core: data provider plugin package

A data provider plugin must subclass :class:`DataProvider` and implement at
least its get_asset() and get_asset_data() methods. Browseable data providers
must implement get_child_assets(). Searchable providers must implement
find_assets(). Finally, read-write providers, must also implement
create_asset(), update_asset(), and delete_asset().
"""
