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
            $table->string('command'); /* add, create, modify, e.t.c. */
            $table->string('target_dn'); /* user or group */
            $table->string('data')->nullable();
            $table->datetime('applied_on')->nullable();
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
