<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

class CreateLdapaction extends Migration
{
    /**
     * Run the migrations.
     *
     * @return void
     */
    public function up()
    {
        Schema::create('ldapactions', function (Blueprint $table) {
            $table->id();
            $table->timestamps();
            // $table->foreignId('hrm_update')->nullable(True)->constrained('h_r_master_updates'); /* */
            $table->foreignId('dataset')->constrained('a_d_datasets'); /* */
            // $table->integer('dataitem')->nullable(); /* */
            $table->string('command'); /* add, create, modify, e.t.c. */
            $table->string('target'); /* user uid or target DN */
            $table->text('data')->nullable();
        });
    }

    /**
     * Reverse the migrations.
     *
     * @return void
     */
    public function down()
    {
        Schema::dropIfExists('ldapactions');
    }
}
