<?php

use Illuminate\Database\Seeder;

class UserSeeder extends Seeder
{
    /**
     * Run the database seeds.
     *
     * @return void
     */
    public function run()
    {
        DB::table('users')->insert([
            'name' => 'apis',
            'email' => 'apis@localhost',
            'password' => Hash::make(Str::random(20)),
            'x_api_key' => env('APIS_X_API_KEY'),
        ]);
    }
}
